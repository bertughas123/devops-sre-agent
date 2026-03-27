"""Risky Tools — Phase 3: Human-Approved Operations with Audit Logging."""
import logging
import docker
from langchain.tools import tool
from utils.security import requires_chainlit_approval
from utils.docker_client import global_docker_client

logger = logging.getLogger("opsguard.risky")

@tool
@requires_chainlit_approval
async def restart_database_risky(reason: str) -> str:
    """
    Restarts the database container (db-prod) via Docker SDK.

    USAGE RULES (WHEN TO USE):
    1. OOM Killer (Exit 137): Observer alarm contains "OOM Killer"
       → Restart is SAFE. No data corruption, just memory exhaustion.
    2. Persistent Disk Issue: After clean_logs succeeds AND db-prod
       is still stopped → Restart to bring it back online.

    PROHIBITIONS (NEVER USE):
    1. Config Error: Observer alarm contains "Config Error"
       → postgresql.conf is corrupted. Restart will crash again.
    2. Data Corruption: Observer alarm contains "DATA CORRUPTION"
       → pg_control is damaged. Restart risks permanent data loss.
    3. Disk Still Full: clean_logs returned "UNSUCCESSFUL"
       → DB cannot start with a full disk. Restart is pointless.

    Args:
        reason: Why the restart is being requested (Agent must explain).

    Returns:
        SUCCESSFUL: db-prod restarted.
        Error: Infrastructure/technical failure.
    """
    try:
        container = global_docker_client.containers.get("db-prod")
        container.restart(timeout=30)

        logger.info(f"DB_RESTART_SUCCESS | reason={reason}")
        return f"SUCCESSFUL: db-prod restarted. Reason: {reason}"

    except docker.errors.NotFound:
        logger.error("DB_RESTART_FAILED | error=container 'db-prod' not found")
        return "Error: Container 'db-prod' not found."

    except docker.errors.APIError as e:
        logger.error(f"DB_RESTART_FAILED | error=Docker API error: {e}")
        return f"Error: Docker API error — {e}"

    except Exception as e:
        logger.error(f"DB_RESTART_FAILED | error=unexpected: {e}")
        return f"Error: Unexpected error — {e}"


@tool
@requires_chainlit_approval
async def simulate_sre_hard_reset(reason: str) -> str:
    """
    Factory Reset: Completely destroys and recreates the db-prod container
    with fresh volumes. This simulates a manual SRE hard intervention.

    USAGE RULES (WHEN TO USE):
    1. Config Error: Observer alarm contains "Config Error"
       → postgresql.conf is corrupted. Only a full reset can fix it.
    2. Data Corruption: Observer alarm contains "DATA CORRUPTION"
       → pg_control is damaged. Volume must be destroyed and recreated.
    3. Persistent Garbage (Exit Code 0): After clean_logs returns UNSUCCESSFUL
       AND restart also fails or is pointless.

    PROHIBITIONS (NEVER USE):
    1. OOM Killer: Simple restart is sufficient. Hard reset is overkill.
    2. Normal disk saturation: clean_logs should handle it first.

    Args:
        reason: Why the hard reset is being requested (Agent must explain).

    Returns:
        SUCCESSFUL: db-prod factory reset complete.
        Error: Infrastructure/technical failure.
    """
    import subprocess

    try:
        # Step 1: Destroy container + associated volumes
        destroy = subprocess.run(
            ["docker-compose", "rm", "-f", "-s", "-v", "db"],
            capture_output=True, text=True, timeout=60
        )

        if destroy.returncode != 0:
            logger.error(f"HARD_RESET_FAILED | phase=destroy | stderr={destroy.stderr}")
            return f"Error: Could not destroy db-prod — {destroy.stderr}"

        # Step 2: Recreate container from scratch (fresh volumes)
        recreate = subprocess.run(
            ["docker-compose", "up", "-d", "db"],
            capture_output=True, text=True, timeout=120
        )

        if recreate.returncode != 0:
            logger.error(f"HARD_RESET_FAILED | phase=recreate | stderr={recreate.stderr}")
            return f"Error: Could not recreate db-prod — {recreate.stderr}"

        logger.info(f"HARD_RESET_SUCCESS | reason={reason}")
        return f"SUCCESSFUL: db-prod factory reset complete. Fresh volumes created. Reason: {reason}"

    except subprocess.TimeoutExpired:
        logger.error("HARD_RESET_FAILED | error=command timed out")
        return "Error: Hard reset timed out."
    except Exception as e:
        logger.error(f"HARD_RESET_FAILED | error={e}")
        return f"Error: Hard reset failed — {e}"
