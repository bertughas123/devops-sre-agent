"""Docker Client Singleton — Centralized connection for all modules.

All modules that need Docker access should import from here:
    from utils.docker_client import global_docker_client

This prevents multiple docker.from_env() calls across the project,
reducing connection overhead and ensuring consistent error handling.
"""
import docker

try:
    global_docker_client = docker.from_env()
except Exception:
    global_docker_client = None
