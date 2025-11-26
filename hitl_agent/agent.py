"""HITL Agent with sub-agents under proposal agent.

Architecture:
    hitl_orchestrator
    ├── proposal_agent (orchestrator for content generation)
    │   ├── sub_agent_1 (customize: e.g., route_planner)
    │   ├── sub_agent_2 (customize: e.g., accommodation_finder)
    │   └── sub_agent_3 (customize: e.g., activity_suggester)
    └── rectification_agent
        └── calls specific sub_agent based on rejection feedback
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .tools import (
    request_human_approval,
    process_human_decision,
    submit_rectified_output,
    finalize_approved_content,
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
# SUB-AGENTS (under proposal_agent)
# Customize these for your use case
# ============================================================================

sub_agent_1 = Agent(
    name="route_planner",
    model=MODEL_ID,
    description="Plans routes, directions, and transportation options",
    instruction=SUB_AGENT_1_PROMPT,
)

sub_agent_2 = Agent(
    name="accommodation_finder",
    model=MODEL_ID,
    description="Finds and recommends accommodations and hotels",
    instruction=SUB_AGENT_2_PROMPT,
)

sub_agent_3 = Agent(
    name="activity_suggester",
    model=MODEL_ID,
    description="Suggests activities, attractions, and things to do",
    instruction=SUB_AGENT_3_PROMPT,
)


# ============================================================================
# PROPOSAL AGENT (orchestrates sub-agents to build complete proposal)
# ============================================================================

proposal_agent = Agent(
    name="proposal_agent",
    model=MODEL_ID,
    description="Orchestrates sub-agents to generate comprehensive proposals",
    instruction=PROPOSAL_AGENT_PROMPT,
    tools=[
        FunctionTool(func=request_human_approval),
    ],
    sub_agents=[
        sub_agent_1,
        sub_agent_2,
        sub_agent_3,
    ],
)


# ============================================================================
# RECTIFICATION AGENT (calls specific sub-agent based on feedback)
# ============================================================================

rectification_agent = Agent(
    name="rectification_agent",
    model=MODEL_ID,
    description="Improves specific parts of rejected content by calling the relevant sub-agent",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_rectified_output),
    ],
    sub_agents=[
        sub_agent_1,
        sub_agent_2,
        sub_agent_3,
    ],
)


# ============================================================================
# ROOT ORCHESTRATOR
# ============================================================================

root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Orchestrates HITL workflow: proposal → approval/reject → finalize or rectify",
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=process_human_decision),
        FunctionTool(func=finalize_approved_content),
    ],
    sub_agents=[
        proposal_agent,
        rectification_agent,
    ],
)
