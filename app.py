"""OpsGuard Main Application — Phase 1 (Autonomous Mode)."""
import asyncio
import chainlit as cl
from core.agent import create_agent
from utils.observer import SystemObserver
from chaos import start_chaos_loop

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
    # Autonomous Trigger (Zero-Touch):
    # When Observer raises an alarm, Agent is invoked automatically.
    # Does NOT wait for the user to say "fix it".
    async def handle_alarm_autonomously(message: str):
        # 1. Notify the UI
        await cl.Message(content=f"🚨 RADAR: {message}\n🤖 OpsGuard Autonomous Intervention Starting...").send()

        # 2. Trigger the agent automatically (do not wait for user!)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent_executor.invoke({"input": f"Emergency: {message}. Resolve autonomously."})
        )

        # 3. Display the agent's result
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

