"""HITL Agent using ADK's SequentialAgent for proposal generation.

Flow:
1. SequentialAgent runs sub-agents in order (route → accommodation → activity)
2. Each agent saves output to state via output_key
3. After sequence completes, ask for human approval ONCE
4. If rejected, only fix the relevant part
"""

from google.adk.agents import LlmAgent, SequentialAgent, Agent
from google.adk.tools import FunctionTool

from .tools import (
    submit_for_approval,
    finalize_approved,
)
from .prompts import (
    ROOT_AGENT_PROMPT,
    RECTIFICATION_AGENT_PROMPT,
    SUB_AGENT_1_PROMPT,
    SUB_AGENT_2_PROMPT,
    SUB_AGENT_3_PROMPT,
    APPROVAL_AGENT_PROMPT,
)


MODEL_ID = "gemini-2.0-flash"


# ============================================================================
# SUB-AGENTS (run sequentially to build proposal)
# Each saves output to state via output_key
# ============================================================================

route_planner = LlmAgent(
    name="route_planner",
    model=MODEL_ID,
    instruction=SUB_AGENT_1_PROMPT,
    output_key="route_plan",  # Saves output to state["route_plan"]
)

accommodation_finder = LlmAgent(
    name="accommodation_finder",
    model=MODEL_ID,
    instruction=SUB_AGENT_2_PROMPT,
    output_key="accommodation_plan",  # Saves output to state["accommodation_plan"]
)

activity_suggester = LlmAgent(
    name="activity_suggester",
    model=MODEL_ID,
    instruction=SUB_AGENT_3_PROMPT,
    output_key="activity_plan",  # Saves output to state["activity_plan"]
)


# ============================================================================
# APPROVAL AGENT (runs after sequence, asks for human approval)
# ============================================================================

approval_agent = LlmAgent(
    name="approval_agent",
    model=MODEL_ID,
    instruction=APPROVAL_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_for_approval),
    ],
)


# ============================================================================
# PROPOSAL AGENT (SequentialAgent - runs sub-agents in order)
# ============================================================================

proposal_agent = SequentialAgent(
    name="proposal_agent",
    description="Generates complete proposal by running sub-agents sequentially",
    sub_agents=[
        route_planner,
        accommodation_finder,
        activity_suggester,
        approval_agent,  # Runs last, combines outputs and asks for approval
    ],
)


# ============================================================================
# RECTIFICATION AGENTS (separate instances for fixing specific parts)
# ============================================================================

route_rectifier = LlmAgent(
    name="route_rectifier",
    model=MODEL_ID,
    instruction=SUB_AGENT_1_PROMPT + "\n\nYou are fixing a route plan based on human feedback. Check state['rejection_feedback'] for what to fix.",
    output_key="route_plan",
)

accommodation_rectifier = LlmAgent(
    name="accommodation_rectifier",
    model=MODEL_ID,
    instruction=SUB_AGENT_2_PROMPT + "\n\nYou are fixing accommodation suggestions based on human feedback. Check state['rejection_feedback'] for what to fix.",
    output_key="accommodation_plan",
)

activity_rectifier = LlmAgent(
    name="activity_rectifier",
    model=MODEL_ID,
    instruction=SUB_AGENT_3_PROMPT + "\n\nYou are fixing activity suggestions based on human feedback. Check state['rejection_feedback'] for what to fix.",
    output_key="activity_plan",
)


# ============================================================================
# RECTIFICATION AGENT
# ============================================================================

rectification_agent = Agent(
    name="rectification_agent",
    model=MODEL_ID,
    description="Fixes specific parts based on rejection feedback",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_for_approval),
    ],
    sub_agents=[
        route_rectifier,
        accommodation_rectifier,
        activity_rectifier,
    ],
)


# ============================================================================
# ROOT AGENT
# ============================================================================

root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Orchestrates HITL workflow",
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=finalize_approved),
    ],
    sub_agents=[
        proposal_agent,
        rectification_agent,
    ],
)
