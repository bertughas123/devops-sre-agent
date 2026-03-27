"""LangChain ReAct Agent Setup — Phase 3 (Hard Reset + Dual-Check)."""
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from core.llm import get_llm
from core.prompt import SYSTEM_PROMPT
from tools.safe import clean_logs, prune_containers
from tools.risky import restart_database_risky, simulate_sre_hard_reset

# Hardcoded ReAct template (offline mode — no hub dependency)
REACT_TEMPLATE = """{system_prompt}

Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

def create_agent():
    """Creates and returns the OpsGuard ReAct agent."""
    llm = get_llm()
    tools = [clean_logs, prune_containers, restart_database_risky, simulate_sre_hard_reset]

    # Build the final prompt by injecting SYSTEM_PROMPT into the template
    prompt_string = REACT_TEMPLATE.replace("{system_prompt}", SYSTEM_PROMPT)
    final_prompt = PromptTemplate.from_template(prompt_string)

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=final_prompt
    )

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,                   # Print reasoning steps to console
        handle_parsing_errors=True,     # Auto-recover from LLM format errors
        max_iterations=15,              # Phase 2: multi-step scenarios need more steps
        return_intermediate_steps=True  # Return intermediate steps for UI
    )

    return executor
