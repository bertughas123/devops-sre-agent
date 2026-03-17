"""Risky Tools — Phase 2: Human-Approved Operations with Audit Logging."""
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
    3. Disk Still Full: clean_logs returned "FAILED"
       → DB cannot start with a full disk. Restart is pointless.

    Args:
        reason: Why the restart is being requested (Agent must explain).

    Returns:
        Success or failure message string.
    """
    try:
        container = global_docker_client.containers.get("db-prod")
        container.restart(timeout=30)

        logger.info(f"DB_RESTART_SUCCESS | reason={reason}")
        return f"db-prod restarted successfully. Reason: {reason}"

    except docker.errors.NotFound:
        logger.error("DB_RESTART_FAILED | error=container 'db-prod' not found")
        return "Restart FAILED: Container 'db-prod' not found."

    except docker.errors.APIError as e:
        logger.error(f"DB_RESTART_FAILED | error=Docker API error: {e}")
        return f"Restart FAILED: Docker API error — {e}"

    except Exception as e:
        logger.error(f"DB_RESTART_FAILED | error=unexpected: {e}")
        return f"Restart FAILED: Unexpected error — {e}"
