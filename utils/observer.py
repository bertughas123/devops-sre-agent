"""Sistem Gözlemcisi (Observer) — Faz 1."""
import os
import asyncio
import subprocess
import docker

class SystemObserver:
    """
    Container'ları periyodik olarak tarayan daemon.
    """
    
    def __init__(self, message_callback=None):
        """
        Args:
            message_callback: async fonksiyon. Alarm mesajını UI'a gönderir.
                Örnek: async def send(msg): await cl.Message(content=msg).send()
        """
        self.message_callback = message_callback
        self.check_interval = int(os.getenv("OBSERVER_INTERVAL", "15"))
        self.web_log_threshold_mb = int(os.getenv("WEB_LOG_THRESHOLD_MB", "100"))
        self.client = docker.from_env()

    def check_disk_usage(self):
        """
        Container'ların log klasör boyutlarını MB cinsinden kontrol eder.
        
        ALARM FARKLILIĞI (ÖNEMLİ):
        - web-prod > WEB_LOG_THRESHOLD_MB → WEB_LOG_SATURATION
        - db-prod > WEB_LOG_THRESHOLD_MB → DB_DISK_CRITICAL (Faz 2'de aktif)
        """
        alarms = []
        
        # Her container'ın izlenecek klasörü ve alarm tipi
        targets = {
            "web-prod": {
                "path": "/var/log",
                "alarm": "WEB_LOG_SATURATION"
            },
            "db-prod": {
                "path": "/var/log",
                "alarm": "DB_DISK_CRITICAL"
            }
        }
        
        for container_name, config in targets.items():
            try:
                result = subprocess.run(
                    f"docker exec {container_name} du -sm {config['path']}",
                    shell=True, capture_output=True, text=True
                )
                # Çıktı formatı: '155    /var/log'
                # İlk sütun = boyut (MB)
                size_mb = int(result.stdout.strip().split()[0])
                
                if size_mb > self.web_log_threshold_mb:
                    alarm_type = config['alarm']
                    if alarm_type == "WEB_LOG_SATURATION":
                        msg = f"⚠️ ALARM: {alarm_type} - web-prod /var/log boyutu {size_mb}MB! (Eşik: {self.web_log_threshold_mb}MB) Loglar şişti!"
                    else:
                        msg = f"🔴 ALARM: {alarm_type} - db-prod /var/log boyutu {size_mb}MB! Çökme Riski!"
                    alarms.append(msg)
            except Exception as e:
                print(f"[OBSERVER] {container_name} disk kontrolü hatası: {e}")
        
        return alarms

    def check_zombie_containers(self):
        """
        Exited durumdaki container'ları sayar.
        
        docker.from_env().containers.list(filters={"status": "exited"})
        ──────────────────────────────────────────────────────────────
        Eşik: 5 container
        - 1-5 arası → Normal (eski container'lar olabilir)
        - 5+ → Alarm! Sistematik sorun var.
        """
        try:
            exited = self.client.containers.list(
                all=True,
                filters={"status": "exited"}
            )
            count = len(exited)
            if count > 5:
                return f"🧟 ALARM: ZOMBIE_OUTBREAK - Sistemde {count} adet ölü container var!"
        except Exception as e:
            print(f"[OBSERVER] Zombi kontrolü hatası: {e}")
        return None

    async def start(self):
        """
        Observer'ın ana döngüsü. Sonsuz çalışır.
        
        Akış:
        1. Disk kontrolü yap → alarm varsa callback'i çağır
        2. Zombi kontrolü yap → alarm varsa callback'i çağır
        3. Interval kadar bekle → tekrar başa dön
        """
        print(f"[OBSERVER] Başlatıldı. Tarama aralığı: {self.check_interval}sn")
        
        while True:
            # Disk kontrolü
            disk_alarms = self.check_disk_usage()
            for alarm in disk_alarms:
                print(f"[OBSERVER] {alarm}")
                if self.message_callback:
                    await self.message_callback(alarm)
            
            # Zombi kontrolü
            zombie_alarm = self.check_zombie_containers()
            if zombie_alarm:
                print(f"[OBSERVER] {zombie_alarm}")
                if self.message_callback:
                    await self.message_callback(zombie_alarm)
            
            await asyncio.sleep(self.check_interval)
