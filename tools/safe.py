"""Safe (Autonomous) Tools — Phase 1."""
import subprocess
from langchain.tools import tool

@tool
def clean_logs(container_name: str) -> str:
    """
    Truncates all log files under /var/log in the specified container.

    Use this tool when a disk saturation alarm is raised.
    Should be called with 'web-prod' for WEB_LOG_SATURATION alarms.

    Args:
        container_name: Target container name (e.g. 'web-prod')

    Returns:
        Cleanup result and current disk status.
    """
    # 1. Truncate logs
    # truncate -s 0 → Resets file size to 0 (clears content, keeps file)
    # *.log → All .log files under /var/log
    truncate_cmd = f"docker exec {container_name} sh -c 'truncate -s 0 /var/log/*.log'"
    subprocess.run(truncate_cmd, shell=True, capture_output=True)
    
    # 2. Check disk status after cleanup
    df_cmd = f"docker exec {container_name} df -h /"
    result = subprocess.run(df_cmd, shell=True, capture_output=True, text=True)
    
    # 3. Parse disk usage percentage
    try:
        lines = result.stdout.strip().split('\n')
        usage = lines[-1].split()[4]  # e.g. "23%"
        return f"{container_name} logs cleaned. Current usage: {usage}."
    except Exception:
        return f"{container_name} logs cleaned. (Could not read disk status)"

@tool
def prune_containers(reason: str) -> str:
    """
    Removes stopped containers and unused resources from the system.

    Should be used when a ZOMBIE_OUTBREAK alarm is raised.

    Args:
        reason: Reason for the cleanup (Agent provides an explanation)

    Returns:
        Cleanup result.
    """
    # docker system prune -f → Removes all stopped containers, unused networks,
    # and dangling images. -f = force (no confirmation prompt)
    result = subprocess.run(
        "docker system prune -f",
        shell=True, capture_output=True, text=True
    )
    return f"System pruned. Reason: {reason}. Zombie containers cleaned."
