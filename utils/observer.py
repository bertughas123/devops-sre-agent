"""System Observer — Phase 1."""
import os
import asyncio
import subprocess
import docker

class SystemObserver:
    """
    Daemon that periodically scans containers for anomalies.
    """
    
    def __init__(self, message_callback=None):
        """
        Args:
            message_callback: Async function that sends alarm messages to the UI.
                Example: async def send(msg): await cl.Message(content=msg).send()
        """
        self.message_callback = message_callback
        self.check_interval = int(os.getenv("OBSERVER_INTERVAL", "15"))
        self.web_log_threshold_mb = int(os.getenv("WEB_LOG_THRESHOLD_MB", "100"))
        self.client = docker.from_env()

        # Monitoring targets: container name -> path & alarm type
        self.targets = {
            "web-prod": {
                "path": "/var/log",
                "alarm": "WEB_LOG_SATURATION"
            },
            "db-prod": {
                "path": "/var/log",
                "alarm": "DB_DISK_CRITICAL"
            }
        }

        # Build active_alarms dynamically from targets + zombie
        self.active_alarms = {name: False for name in self.targets}
        self.active_alarms["zombie"] = False

    def check_disk_usage(self):
        """
        Checks log directory sizes (in MB) for all monitored containers.

        Iterates over self.targets and raises an alarm if the directory
        size exceeds self.web_log_threshold_mb.
        """
        alarms = []

        for container_name, config in self.targets.items():
            try:
                result = subprocess.run(
                    f"docker exec {container_name} du -sm {config['path']}",
                    shell=True, capture_output=True, text=True
                )
                # Output format: '155    /var/log'
                # First column = size (MB)
                size_mb = int(result.stdout.strip().split()[0])

                if size_mb > self.web_log_threshold_mb:
                    if not self.active_alarms[container_name]:
                        self.active_alarms[container_name] = True
                        alarm_type = config['alarm']
                        msg = (
                            f"⚠️ ALARM: {alarm_type} - {container_name} "
                            f"{config['path']} size is {size_mb}MB! "
                            f"(Threshold: {self.web_log_threshold_mb}MB)"
                        )
                        alarms.append(msg)
                else:
                    self.active_alarms[container_name] = False
            except Exception as e:
                print(f"[OBSERVER] {container_name} disk check error: {e}")

        return alarms

    def check_zombie_containers(self):
        """
        Counts containers in Exited state.

        docker.from_env().containers.list(filters={"status": "exited"})
        ──────────────────────────────────────────────────────────────
        Threshold: 5 containers
        - 1-5 → Normal (old containers may exist)
        - 5+  → Alarm! Systematic issue detected.
        """
        try:
            exited = self.client.containers.list(all=True, filters={"status": "exited"})
            count = len(exited)

            if count > 5:
                if not self.active_alarms["zombie"]:
                    self.active_alarms["zombie"] = True
                    return [f"🧟 ALARM: ZOMBIE_OUTBREAK - {count} dead containers detected in the system!"]
            else:
                self.active_alarms["zombie"] = False

        except Exception as e:
            print(f"[OBSERVER] Zombie check error: {e}")

        return []

    async def start(self):
        """
        Main observer loop. Runs indefinitely.

        Flow:
        1. Run all sensors concurrently (asyncio.to_thread + gather)
        2. Process results → invoke callback if alarms exist
        3. Sleep for interval → repeat
        """
        print(f"[OBSERVER] Started. Scan interval: {self.check_interval}s")

        # Sensor list (Registry Pattern)
        sensors = [self.check_disk_usage, self.check_zombie_containers]

        while True:
            # 1. Run all sensors CONCURRENTLY in background threads
            tasks = [asyncio.to_thread(sensor) for sensor in sensors]

            # 2. Wait for all results (prevents blocking)
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 3. Process results in a standardized way
            for result in results:
                if isinstance(result, Exception):
                    print(f"[OBSERVER] Sensor execution error: {result}")
                    continue

                if isinstance(result, list) and result:
                    for alarm in result:
                        print(f"[OBSERVER] {alarm}")
                        if self.message_callback:
                            await self.message_callback(alarm)

            await asyncio.sleep(self.check_interval)
