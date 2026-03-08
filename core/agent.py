"""LangChain ReAct Agent Setup — Phase 1 (LangSmith Hub)."""
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain import hub

from core.llm import get_llm
from core.prompt import SYSTEM_PROMPT
from tools.safe import clean_logs, prune_containers

def create_agent():
    """
    Creates and returns the OpsGuard ReAct agent.

    Architecture:
    1. Pull official ReAct template from LangSmith Hub (hwchase17/react).
    2. Prepend our SYSTEM_PROMPT to inject OpsGuard-specific rules.
    3. Wrap in AgentExecutor with safety guards.

    Returns:
        AgentExecutor: Ready-to-run agent instance.
    """
    llm = get_llm()
    tools = [clean_logs, prune_containers]

    # 1. Pull the official ReAct prompt from LangSmith Hub
    # This template includes: {tools}, {tool_names}, {input}, {agent_scratchpad}
    base_prompt = hub.pull("hwchase17/react")

    # 2. Prepend our SYSTEM_PROMPT to the hub template
    # This injects OpsGuard alarm rules at the top of the prompt
    final_prompt = PromptTemplate(
        template=SYSTEM_PROMPT + "\n\n" + base_prompt.template,
        input_variables=base_prompt.input_variables
    )

    # 3. Create the ReAct agent with the combined prompt
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=final_prompt
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,                   # Print reasoning steps to console (debug)
        handle_parsing_errors=True,     # Auto-recover from LLM format errors
        max_iterations=10,              # Prevent infinite reasoning loops
        return_intermediate_steps=True  # Return intermediate steps for UI display
    )

    return executor
