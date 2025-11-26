"""HITL Agent using SequentialAgent + require_confirmation=True.

The key is using FunctionTool(..., require_confirmation=True) which makes
ADK pause and ask for human confirmation before executing the tool.
"""

from google.adk.agents import LlmAgent, SequentialAgent, Agent
from google.adk.tools import FunctionTool

from .tools import execute_proposal, submit_rectified
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
# SUB-AGENTS (run sequentially)
# ============================================================================

route_planner = LlmAgent(
    name="route_planner",
    model=MODEL_ID,
    instruction=SUB_AGENT_1_PROMPT,
    output_key="route_plan",
)

accommodation_finder = LlmAgent(
    name="accommodation_finder",
    model=MODEL_ID,
    instruction=SUB_AGENT_2_PROMPT,
    output_key="accommodation_plan",
)

activity_suggester = LlmAgent(
    name="activity_suggester",
    model=MODEL_ID,
    instruction=SUB_AGENT_3_PROMPT,
    output_key="activity_plan",
)


# ============================================================================
# APPROVAL AGENT - uses require_confirmation=True for HITL
# ============================================================================

approval_agent = LlmAgent(
    name="approval_agent",
    model=MODEL_ID,
    instruction=APPROVAL_AGENT_PROMPT,
    tools=[
        # require_confirmation=True makes ADK pause for human approval
        FunctionTool(func=execute_proposal, require_confirmation=True),
    ],
)


# ============================================================================
# PROPOSAL AGENT (SequentialAgent)
# ============================================================================

proposal_agent = SequentialAgent(
    name="proposal_agent",
    description="Generates proposal sequentially, then asks for confirmation",
    sub_agents=[
        route_planner,
        accommodation_finder,
        activity_suggester,
        approval_agent,
    ],
)


# ============================================================================
# RECTIFICATION AGENTS
# ============================================================================

route_rectifier = LlmAgent(
    name="route_rectifier",
    model=MODEL_ID,
    instruction=SUB_AGENT_1_PROMPT + "\n\nFix the route based on feedback in state['rejection_feedback'].",
    output_key="route_plan",
)

accommodation_rectifier = LlmAgent(
    name="accommodation_rectifier",
    model=MODEL_ID,
    instruction=SUB_AGENT_2_PROMPT + "\n\nFix accommodations based on feedback in state['rejection_feedback'].",
    output_key="accommodation_plan",
)

activity_rectifier = LlmAgent(
    name="activity_rectifier",
    model=MODEL_ID,
    instruction=SUB_AGENT_3_PROMPT + "\n\nFix activities based on feedback in state['rejection_feedback'].",
    output_key="activity_plan",
)


# ============================================================================
# RECTIFICATION AGENT
# ============================================================================

rectification_agent = Agent(
    name="rectification_agent",
    model=MODEL_ID,
    description="Fixes specific parts based on feedback",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        # Also requires confirmation for the rectified version
        FunctionTool(func=submit_rectified, require_confirmation=True),
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
    sub_agents=[
        proposal_agent,
        rectification_agent,
    ],
)
