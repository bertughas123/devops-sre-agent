"""Chaos Runner — Exhaustible loop for Phase 1 & Phase 2 (Shuffle & Pop)."""
import os
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


def start_chaos_loop():
    """
    Runs all chaos scenarios exactly once in randomized order (Shuffle & Pop).

    Phase 1 + Phase 2 = 6 scenarios.
    Each scenario is drawn from the deck like a card, never repeated.
    The engine stops gracefully when all scenarios have been executed.

    Intervals are dynamic based on LLM_PROVIDER:
    - gemini: 150-250s (fast cloud API, but above 120s approval timeout)
    - ollama: 450-650s (slow local model needs more thinking time)
    Overridable via CHAOS_INTERVAL_MIN / CHAOS_INTERVAL_MAX env vars.
    """
    # Dynamic interval calculation based on LLM provider
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "gemini":
        default_min, default_max = 150, 250
    else:
        default_min, default_max = 450, 650

    interval_min = int(os.getenv("CHAOS_INTERVAL_MIN", default_min))
    interval_max = int(os.getenv("CHAOS_INTERVAL_MAX", default_max))

    logger.info(f"Intervals configured: {interval_min}-{interval_max}s (provider: {provider})")

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
