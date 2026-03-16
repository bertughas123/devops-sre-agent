"""Security Decorator — Phase 2: Human Approval Gate with Audit Logging."""
import functools
import asyncio
import logging
import chainlit as cl

# Module-level audit logger
logger = logging.getLogger("opsguard.security")

# Timeout in seconds for human approval
APPROVAL_TIMEOUT = 120


def requires_chainlit_approval(func):
    """
    Adds an 'Approval Gate' with audit logging and timeout to risky functions.

    How the Decorator Works:
    ─────────────────────────
    Normal flow:    tool is called → executes immediately → returns result
    Approved flow:  tool is called → UI button appears → user selects
                    → Approve: executes → Reject: returns "Rejected"
                    → Timeout (120s): auto-rejects and logs warning

    Enterprise Features:
    ─────────────────────
    1. Audit Logging: Every approval request, approval, rejection, and
       timeout is logged via Python's logging module for compliance.
    2. Timeout: asyncio.wait_for prevents the agent from hanging
       indefinitely if no human responds within APPROVAL_TIMEOUT seconds.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        reason = kwargs.get("reason", args[0] if args else "Reason not provided")

        # AUDIT: Log the approval request
        logger.info(f"APPROVAL_REQUESTED | tool={func_name} | reason={reason}")

        actions = [
            cl.Action(name="approve", label="✅ Approve", value="approved"),
            cl.Action(name="reject", label="❌ Reject", value="rejected"),
        ]

        try:
            # Wrap the Chainlit UI call with a timeout
            response = await asyncio.wait_for(
                cl.AskActionMessage(
                    content=(
                        f"**Approval Required!**\n\n"
                        f"The Agent wants to execute: **{func_name}**\n"
                        f"Reason: **{reason}**\n\n"
                        f"Do you approve this action?"
                    ),
                    actions=actions
                ).send(),
                timeout=APPROVAL_TIMEOUT
            )
        except asyncio.TimeoutError:
            # AUDIT: Log timeout
            logger.warning(f"APPROVAL_TIMEOUT | tool={func_name} | timeout={APPROVAL_TIMEOUT}s")
            return f"Operation '{func_name}' timed out after {APPROVAL_TIMEOUT}s. Auto-rejected."

        if response and response.get("value") == "approved":
            # AUDIT: Log approval
            logger.info(f"APPROVED | tool={func_name}")
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) \
                   else func(*args, **kwargs)
        else:
            # AUDIT: Log rejection
            logger.warning(f"REJECTED | tool={func_name}")
            return "Operation rejected by the user."

    return wrapper
