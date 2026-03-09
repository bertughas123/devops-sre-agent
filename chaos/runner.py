"""Chaos Runner — Background thread loop for Phase 1."""
import time
import threading
import random

from chaos.scenarios import fill_web_disk_trigger, create_zombie_containers


def start_chaos_loop(interval_min=450, interval_max=650):
    """
    Runs random chaos scenarios in a background daemon thread.

    Critical design decision: interval_min=180 (3 minutes)
    - Observer will look back 2 minutes into logs (Phase 2).
    - If chaos interval < 2min, Observer may still be processing
      the previous alarm when a new chaos hits — collision!
    - Therefore: chaos interval (3-5min) > observer window (2min).

    Threading notes:
    - daemon=True — thread dies when the main program exits.
    - Does not block the main program.
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
                print(f"[CHAOS] Error: {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("[CHAOS] Chaos loop started.")
