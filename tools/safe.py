"""Safe (Autonomous) Tools — Phase 2 (Docker SDK + Feedback)."""
import docker
from langchain.tools import tool
from utils.docker_client import global_docker_client as client

@tool
def clean_logs(container_name: str) -> str:
    """
    Truncates all .log files under /var/log in the specified container.

    Use this tool when a disk saturation alarm is raised.
    After cleanup, measures /var/log size and reports the result.

    Args:
        container_name: Target container name (e.g. 'web-prod', 'db-prod')

    Returns:
        SUCCESSFUL: /var/log size dropped below 100MB.
        UNSUCCESSFUL: /var/log is still 100MB or above (non-log data exists).
    """
    try:
        container = client.containers.get(container_name)

        # 1. Truncate all log files inside the container
        container.exec_run("sh -c 'truncate -s 0 /var/log/*.log'")

        # 2. Measure /var/log size after cleanup (du -sm = size in MB)
        exit_code, output = container.exec_run("du -sm /var/log")

        # 3. Parse MB value from output (format: b'42\t/var/log\n')
        size_mb = int(output.decode('utf-8').strip().split()[0])

        # 4. Evaluate result (threshold: 100MB)
        if size_mb < 100:
            return f"SUCCESSFUL: {container_name} logs cleaned. /var/log size: {size_mb}MB."
        else:
            return (
                f"UNSUCCESSFUL: {container_name} logs cleaned BUT /var/log is still "
                f"{size_mb}MB! (Persistent non-log data exists — clean_logs is insufficient)."
            )
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
