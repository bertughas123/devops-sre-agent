"""Chaos Scenarios — Phase 1: Web Disk & Zombie."""
import subprocess
import random
import docker


def fill_web_disk_trigger():
    """
    Writes 150MB of garbage data to /var/log inside web-prod container.

    Why /var/log?
    - Standard directory where Nginx writes its logs.
    - Agent's clean_logs tool targets this directory.
    - Simulates a real-world scenario where log rotation is misconfigured.

    Why 150MB (instead of 2GB)?
    - Observer now monitors directory size (du -sm), not disk percentage.
    - WEB_LOG_THRESHOLD_MB=100 — writing 150MB is enough to trigger the alarm.
    - Does not waste SSD lifespan; test cycle completes much faster.
    """
    cmd = (
        "docker exec web-prod "
        "dd if=/dev/zero of=/var/log/chaos_garbage.log bs=1M count=150"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return "Chaos: Web server (web-prod) log area filled (150MB)."


def create_zombie_containers(count=15):
    """
    Creates dead (Exited) containers to pollute the system.

    Real-world equivalent:
    - Uncleared test containers from CI/CD pipelines.
    - Accumulated old containers in developer environments.

    Why Docker SDK (instead of subprocess)?
    - subprocess.run: Opens a new shell per iteration — slow.
    - Docker SDK: Connects to Docker Daemon directly via REST API — fast.
    """
    # Connect to Docker Daemon (once, before the loop)
    client = docker.from_env()
    created_count = 0

    for i in range(count):
        name = f"zombie-{i}-{random.randint(1000, 9999)}"
        try:
            # detach=True — code does NOT wait for the container to finish.
            # Container runs in background (echo zombie → exits immediately → Exited).
            client.containers.run(
                image="alpine",
                command="echo zombie",
                name=name,
                detach=True
            )
            created_count += 1
        except docker.errors.ImageNotFound:
            # Alpine image not found — cannot pull from Docker Hub.
            # No point continuing the loop; all iterations will fail.
            print("[CHAOS] ERROR: 'alpine' image not found!")
            break
        except docker.errors.APIError as e:
            # Name conflict, resource limit, etc.
            # Skip this container but continue the loop.
            print(f"[CHAOS] API Error ({name}): {e}")
            continue

    return f"Chaos: {created_count} zombie containers created (via SDK)."
