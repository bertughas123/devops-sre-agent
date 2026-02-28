"""Kaos Senaryoları — Faz 1: Web Disk & Zombi."""
import subprocess
import random
import time
import threading
import docker

def fill_web_disk_trigger():
    """
    web-prod container'ının /var/log dizinine 2GB çöp veri yazar.
    
    Neden /var/log?
    - Nginx loglarının yazıldığı standart dizin.
    - Agent'ın clean_logs tool'u bu dizini hedef alır.
    - Gerçek hayatta log rotation yapılmadığında olan senaryo.
    """
    cmd = (
        "docker exec web-prod "
        "dd if=/dev/zero of=/var/log/chaos_garbage.log bs=1M count=2000"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return "Chaos: Web sunucusu (web-prod) log alanı dolduruldu."

def create_zombie_containers(count=15):
    """
    'Exited' durumda kalan ölü container'lar üretir.
    
    Gerçek Hayat Karşılığı:
    - CI/CD pipeline'larında temizlenmeyen test container'ları.
    - Geliştirici ortamlarında biriken eski container'lar.
    
    Neden Docker SDK (subprocess yerine)?
    ─────────────────────────────────────
    - subprocess.run: Her döngüde yeni bir shell açar → Yavaş.
    - Docker SDK: Docker Daemon'a doğrudan REST API üzerinden bağlanır → Hızlı.
    """
    # Docker Daemon'a bağlan (bir kez, döngüden önce)
    client = docker.from_env()
    created_count = 0
    
    for i in range(count):
        name = f"zombie-{i}-{random.randint(1000, 9999)}"
        try:
            # detach=True → Kod container'ın bitmesini BEKLEMEZ.
            # Container arka planda çalışır (echo zombie → hemen kapanır → Exited).
            # subprocess'te bu davranış yoktu — her container için shell bloke oluyordu.
            client.containers.run(
                image="alpine",
                command="echo zombie",
                name=name,
                detach=True
            )
            created_count += 1
        except docker.errors.ImageNotFound:
            # Alpine imajı yoksa → Docker Hub'dan çekilememiş.
            # Döngüyü devam ettirmenin anlamı yok, hepsi başarısız olacak.
            print("[CHAOS] HATA: 'alpine' imajı bulunamadı!")
            break
        except docker.errors.APIError as e:
            # İsim çakışması, kaynak limiti vb. API hataları.
            # Bu container'ı atla ama döngüye devam et.
            print(f"[CHAOS] API Hatası ({name}): {e}")
            continue
    
    return f"Chaos: {created_count} adet zombi container (SDK ile) oluşturuldu."

def start_chaos_loop(interval_min=180, interval_max=300):
    """
    Arka planda rastgele kaos senaryoları çalıştırır.
    
    KRİTİK TASARIM KARARI: interval_min=180 (3 dakika)
    ─────────────────────────────────────────────────────
    Observer loglara geriye dönük 2 dakika bakacak (Faz 2).
    Eğer chaos aralığı < 2 dakika olursa, Observer henüz
    önceki alarmı işlerken yeni bir chaos gelir → Çakışma!
    
    Bu yüzden: chaos aralığı (3-5dk) > observer penceresi (2dk)
    
    Threading Notu:
    - daemon=True → Ana program kapanınca thread de kapanır.
    - Ana programı bloke etmez.
    """
    def _loop():
        scenarios = [fill_web_disk_trigger, create_zombie_containers]
        while True:
            wait = random.randint(interval_min, interval_max)
            time.sleep(wait)
            scenario = random.choice(scenarios)
            try:
                result = scenario()
                print(f"[CHAOS] {result}")
            except Exception as e:
                print(f"[CHAOS] Hata: {e}")
    
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("[CHAOS] Kaos döngüsü başlatıldı.")
