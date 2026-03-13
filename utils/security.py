"""Security Decorator — Phase 2: Human Approval Gate."""
import functools
import asyncio
import chainlit as cl

def requires_chainlit_approval(func):
    """
    Adds an 'Approval Gate' to risky functions.
    
    How the Decorator Works:
    ─────────────────────────
    Normal flow:    tool is called → executes immediately → returns result
    Approved flow:  tool is called → UI button appears → user selects
                    → Approve: executes → Reject: returns "Rejected"
    
    Technical Details:
    ─────────────────
    1. @functools.wraps(func) → Preserves original function's name and docstring.
       Without this, LangChain would see the tool's name as 'wrapper'.
    
    2. cl.AskActionMessage → Chainlit's built-in "button question" widget.
       Shows two buttons in the UI and waits for the user to click.
    
    3. async def wrapper → Decorator must be async because:
       - cl.AskActionMessage.send() is async (requires await)
       - It runs in Chainlit's event loop
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get function name and reason
        func_name = func.__name__
        reason = kwargs.get("reason", args[0] if args else "Reason not provided")
        
        # Request approval in UI
        actions = [
            cl.Action(name="approve", label="✅ Approve", value="approved"),
            cl.Action(name="reject", label="❌ Reject", value="rejected"),
        ]
        
        response = await cl.AskActionMessage(
            content=(
                f"**Approval Required!**\n\n"
                f"The Agent wants to execute: **{func_name}**\n"
                f"Reason: **{reason}**\n\n"
                f"Do you approve this action?"
            ),
            actions=actions
        ).send()
        
        # Evaluate user's decision
        if response and response.get("value") == "approved":
            # Approved → Execute the actual function
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) \
                   else func(*args, **kwargs)
        else:
            # Rejected → Notify the Agent
            return "Operation rejected by the user."
    
    return wrapper
