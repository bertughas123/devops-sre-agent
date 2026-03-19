"""OpsGuard Main Application — Phase 2 (Autonomous + Human-in-the-Loop)."""
import asyncio
import sys
import logging
import chainlit as cl
from core.agent import create_agent
from utils.observer import SystemObserver
from chaos.runner import start_chaos_loop

# ── Centralized Logging Configuration ──
logger = logging.getLogger("opsguard")
logger.setLevel(logging.INFO)

# Hot-Reload Protection: Chainlit reloads app.py on file changes.
# Without this guard, duplicate handlers would be added on every reload,
# causing each log line to appear multiple times in the output.
if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
    )

    # Handler 1: Persistent audit log file (append mode, UTF-8)
    file_handler = logging.FileHandler("opsguard_audit.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Handler 2: Live terminal output via stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# Global agent and observer (shared across all sessions)
agent_executor = None
observer = None

@cl.on_chat_start
async def start():
    """
    Runs when a Chainlit session starts.

    Architecture:
    1. Agent is GLOBAL — recreating per message is expensive.
    2. Observer runs as BACKGROUND async task via asyncio.create_task.
    3. Chaos runs in a separate daemon thread.
    """
    global agent_executor, observer

    # 1. Create the agent
    agent_executor = create_agent()

    # 2. Start the Observer
    async def handle_alarm_autonomously(message: str):
        await cl.Message(content=f"🚨 RADAR: {message}\n🤖 OpsGuard Autonomous Intervention Starting...").send()

        # ainvoke preserves Chainlit's async context, allowing
        # @requires_chainlit_approval UI buttons to render correctly.
        result = await agent_executor.ainvoke(
            {"input": f"Emergency: {message}. Resolve autonomously."}
        )

        output = result.get("output", "No response generated.")
        await cl.Message(content=f"🛡️ OPSGUARD REPORT:\n{output}").send()

    observer = SystemObserver(message_callback=handle_alarm_autonomously)
    asyncio.create_task(observer.start())

    # 3. Start the chaos loop (background daemon thread)
    start_chaos_loop()

    await cl.Message(content="🛡️ OpsGuard Active — Autonomous mode. Monitoring system...").send()

@cl.on_message
async def main(message: cl.Message):
    """
    Blocks manual user commands in autonomous mode.

    OpsGuard Phase 1 operates in Zero-Touch mode:
    only the Observer can trigger the agent via alarms.
    """
    await cl.Message(
        content=(
            "🛑 **Autonomous Mode Active!**\n\n"
            "OpsGuard is not accepting manual commands at this time. "
            "I am configured to only respond to radar detections autonomously. "
            "Please wait for the background chaos to trigger the system."
        )
    ).send()

