"""HITL Agent with multi-agent flow: proposal → approval → next agent."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .tools import (
    request_human_approval,
    process_human_decision,
    submit_rectified_output,
    execute_next_step,
)
from .prompts import (
    ROOT_AGENT_PROMPT,
    PROPOSAL_AGENT_PROMPT,
    RECTIFICATION_AGENT_PROMPT,
    NEXT_AGENT_PROMPT,
)


MODEL_ID = "gemini-2.0-flash"


# Agent 1: Proposal Agent - generates content and asks for approval
proposal_agent = Agent(
    name="proposal_agent",
    model=MODEL_ID,
    description="Generates content based on user request and submits for human approval",
    instruction=PROPOSAL_AGENT_PROMPT,
    tools=[
        FunctionTool(func=request_human_approval),
    ],
)


# Agent 2: Rectification Agent - improves rejected content
rectification_agent = Agent(
    name="rectification_agent",
    model=MODEL_ID,
    description="Improves rejected content based on human feedback",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_rectified_output),
    ],
)


# Agent 3: Next Agent - handles post-approval tasks (customize this for your use case)
next_agent = Agent(
    name="next_agent",
    model=MODEL_ID,
    description="Executes the next step after proposal is approved",
    instruction=NEXT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=execute_next_step),
    ],
)


# Root Orchestrator - routes to the right agent based on state
root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Orchestrates HITL workflow: proposal → approval → next agent",
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=process_human_decision),
    ],
    sub_agents=[
        proposal_agent,
        rectification_agent,
        next_agent,
    ],
)
