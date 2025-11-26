"""Main HITL Agent with sub-agents for proposal, rectification, and processing."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .tools import (
    request_human_approval,
    process_human_decision,
    submit_rectified_output,
    execute_approved_action,
)
from .prompts import (
    ROOT_AGENT_PROMPT,
    PROPOSAL_AGENT_PROMPT,
    RECTIFICATION_AGENT_PROMPT,
    PROCESSOR_AGENT_PROMPT,
)
from .callbacks import before_agent_callback


# Default model - can be overridden via environment or config
MODEL_ID = "gemini-2.0-flash"


# Create the Proposal Agent
proposal_agent = Agent(
    name="proposal_agent",
    model=MODEL_ID,
    description="Generates proposals/outputs and submits them for human approval",
    instruction=PROPOSAL_AGENT_PROMPT,
    tools=[
        FunctionTool(func=request_human_approval),
    ],
)


# Create the Rectification Agent
rectification_agent = Agent(
    name="rectification_agent",
    model=MODEL_ID,
    description="Improves rejected proposals based on human feedback",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_rectified_output),
    ],
)


# Create the Processor Agent
processor_agent = Agent(
    name="processor_agent",
    model=MODEL_ID,
    description="Executes approved proposals and reports results",
    instruction=PROCESSOR_AGENT_PROMPT,
    tools=[
        FunctionTool(func=execute_approved_action),
    ],
)


# Create the Root Agent (Orchestrator)
root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Human-in-the-Loop Orchestrator that manages proposal, approval, and processing workflow",
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=process_human_decision),
    ],
    sub_agents=[
        proposal_agent,
        rectification_agent,
        processor_agent,
    ],
    before_agent_callback=before_agent_callback,
)

