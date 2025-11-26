"""HITL Agent using ADK's built-in confirmation mechanism.

Uses tool_context.request_confirmation() for true human-in-the-loop.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .tools import (
    submit_for_approval,
    rectify_proposal,
    finalize_approved,
)
from .prompts import (
    ROOT_AGENT_PROMPT,
    PROPOSAL_AGENT_PROMPT,
    RECTIFICATION_AGENT_PROMPT,
    SUB_AGENT_1_PROMPT,
    SUB_AGENT_2_PROMPT,
    SUB_AGENT_3_PROMPT,
)


MODEL_ID = "gemini-2.0-flash"


# ============================================================================
# SUB-AGENTS FOR PROPOSAL GENERATION
# ============================================================================

route_planner = Agent(
    name="route_planner",
    model=MODEL_ID,
    description="Plans routes, directions, and transportation",
    instruction=SUB_AGENT_1_PROMPT,
)

accommodation_finder = Agent(
    name="accommodation_finder",
    model=MODEL_ID,
    description="Finds hotels and accommodations",
    instruction=SUB_AGENT_2_PROMPT,
)

activity_suggester = Agent(
    name="activity_suggester",
    model=MODEL_ID,
    description="Suggests activities and attractions",
    instruction=SUB_AGENT_3_PROMPT,
)


# ============================================================================
# SUB-AGENTS FOR RECTIFICATION (separate instances)
# ============================================================================

route_rectifier = Agent(
    name="route_rectifier",
    model=MODEL_ID,
    description="Fixes route issues based on feedback",
    instruction=SUB_AGENT_1_PROMPT + "\n\nFix the route based on human feedback.",
)

accommodation_rectifier = Agent(
    name="accommodation_rectifier",
    model=MODEL_ID,
    description="Fixes accommodation issues based on feedback",
    instruction=SUB_AGENT_2_PROMPT + "\n\nFix accommodations based on human feedback.",
)

activity_rectifier = Agent(
    name="activity_rectifier",
    model=MODEL_ID,
    description="Fixes activity suggestions based on feedback",
    instruction=SUB_AGENT_3_PROMPT + "\n\nFix activities based on human feedback.",
)


# ============================================================================
# PROPOSAL AGENT
# ============================================================================

proposal_agent = Agent(
    name="proposal_agent",
    model=MODEL_ID,
    description="Generates proposals using sub-agents and submits for approval",
    instruction=PROPOSAL_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_for_approval),
    ],
    sub_agents=[
        route_planner,
        accommodation_finder,
        activity_suggester,
    ],
)


# ============================================================================
# RECTIFICATION AGENT
# ============================================================================

rectification_agent = Agent(
    name="rectification_agent",
    model=MODEL_ID,
    description="Fixes rejected proposals using specific sub-agents",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        FunctionTool(func=rectify_proposal),
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
    description="Orchestrates HITL workflow with built-in confirmation",
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=finalize_approved),
    ],
    sub_agents=[
        proposal_agent,
        rectification_agent,
    ],
)
