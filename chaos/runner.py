"""Chaos Runner — Exhaustible loop for Phase 1 & Phase 2 (Shuffle & Pop)."""
import time
import logging
import threading
import random

logger = logging.getLogger("opsguard.chaos")

from chaos.scenarios import (
    fill_web_disk_trigger,
    create_zombie_containers,
    trigger_db_garbage_flood,
    trigger_config_corruption,
    trigger_oom_kill,
    trigger_data_corruption,
)


def start_chaos_loop(interval_min=450, interval_max=650):
    """
    Runs all chaos scenarios exactly once in randomized order (Shuffle & Pop).

    Phase 1 + Phase 2 = 6 scenarios.
    Each scenario is drawn from the deck like a card, never repeated.
    The engine stops gracefully when all scenarios have been executed.
    """
    def _loop():
        scenarios = [
            fill_web_disk_trigger,
            create_zombie_containers,
            trigger_db_garbage_flood,
            trigger_config_corruption,
            trigger_oom_kill,
            trigger_data_corruption,
        ]
        random.shuffle(scenarios)

        while scenarios:
            wait = random.randint(interval_min, interval_max)
            logger.info(f"Next scenario in {wait}s. Remaining tests: {len(scenarios)}")
            time.sleep(wait)
            scenario = scenarios.pop()
            try:
                result = scenario()
                logger.info(f"{result}")
            except Exception as e:
                logger.error(f"Scenario execution error: {e}")

        logger.info("All chaos scenarios executed successfully. Engine stopping.")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("Chaos loop started.")
