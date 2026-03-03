"""Safe (Autonomous) Tools — Phase 1 (Docker SDK)."""
import docker
from langchain.tools import tool

# Module-level Docker client (single connection, reused by all tools)
client = docker.from_env()

@tool
def clean_logs(container_name: str) -> str:
    """
    Truncates all log files under /var/log in the specified container.

    Use this tool when a disk saturation alarm is raised.
    Should be called with 'web-prod' for WEB_LOG_SATURATION alarms.

    Args:
        container_name: Target container name (e.g. 'web-prod')

    Returns:
        Cleanup result with current /var/log size in MB.
    """
    try:
        container = client.containers.get(container_name)

        # 1. Truncate all log files inside the container
        # sh -c is required for wildcard (*) expansion
        container.exec_run("sh -c 'truncate -s 0 /var/log/*.log'")

        # 2. Check directory size after cleanup (du -sm = size in MB)
        exit_code, output = container.exec_run("du -sm /var/log")

        # 3. Parse MB value from output (format: b'155\t/var/log\n')
        size_mb = int(output.decode().strip().split()[0])

        return f"{container_name} logs cleaned. Current /var/log size: {size_mb}MB."

    except docker.errors.NotFound:
        return f"Error: Container '{container_name}' not found."
    except Exception as e:
        return f"Error cleaning logs on {container_name}: {e}"

@tool
def prune_containers(reason: str) -> str:
    """
    Removes stopped containers and unused resources from the system.

    Should be used when a ZOMBIE_OUTBREAK alarm is raised.

    Args:
        reason: Reason for the cleanup (Agent provides an explanation)

    Returns:
        Cleanup result with deleted count and reclaimed space.
    """
    try:
        # client.containers.prune() returns a dict:
        # {'ContainersDeleted': ['id1', 'id2', ...], 'SpaceReclaimed': 12345678}
        result = client.containers.prune()

        deleted_list = result.get("ContainersDeleted", None) or []
        deleted_count = len(deleted_list)

        space_bytes = result.get("SpaceReclaimed", 0)
        space_mb = round(space_bytes / (1024 * 1024), 2)

        return (
            f"System pruned. Reason: {reason}. "
            f"Deleted: {deleted_count} containers. Reclaimed: {space_mb}MB."
        )
    except Exception as e:
        return f"Error during prune: {e}"
