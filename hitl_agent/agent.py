"""HITL Agent with sub-agents under proposal agent.

Architecture:
    hitl_orchestrator (root)
    ├── proposal_agent
    │   ├── route_planner
    │   ├── accommodation_finder
    │   └── activity_suggester
    └── rectification_agent
        ├── route_planner_rectifier (separate instance)
        ├── accommodation_rectifier (separate instance)
        └── activity_rectifier (separate instance)
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
# SUB-AGENTS FOR PROPOSAL_AGENT
# ============================================================================

route_planner = Agent(
    name="route_planner",
    model=MODEL_ID,
    description="Plans routes, directions, and transportation options",
    instruction=SUB_AGENT_1_PROMPT,
)

accommodation_finder = Agent(
    name="accommodation_finder",
    model=MODEL_ID,
    description="Finds and recommends accommodations and hotels",
    instruction=SUB_AGENT_2_PROMPT,
)

activity_suggester = Agent(
    name="activity_suggester",
    model=MODEL_ID,
    description="Suggests activities, attractions, and things to do",
    instruction=SUB_AGENT_3_PROMPT,
)


# ============================================================================
# SUB-AGENTS FOR RECTIFICATION_AGENT (separate instances)
# ============================================================================

route_planner_rectifier = Agent(
    name="route_planner_rectifier",
    model=MODEL_ID,
    description="Fixes route/transportation issues based on feedback",
    instruction=SUB_AGENT_1_PROMPT + "\n\nYou are fixing a previously rejected route plan based on user feedback.",
)

accommodation_rectifier = Agent(
    name="accommodation_rectifier",
    model=MODEL_ID,
    description="Fixes accommodation recommendations based on feedback",
    instruction=SUB_AGENT_2_PROMPT + "\n\nYou are fixing previously rejected accommodation suggestions based on user feedback.",
)

activity_rectifier = Agent(
    name="activity_rectifier",
    model=MODEL_ID,
    description="Fixes activity suggestions based on feedback",
    instruction=SUB_AGENT_3_PROMPT + "\n\nYou are fixing previously rejected activity suggestions based on user feedback.",
)


# ============================================================================
# PROPOSAL AGENT
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
    description="Fixes specific parts of rejected content using relevant sub-agent",
    instruction=RECTIFICATION_AGENT_PROMPT,
    tools=[
        FunctionTool(func=submit_rectified_output),
    ],
    sub_agents=[
        route_planner_rectifier,
        accommodation_rectifier,
        activity_rectifier,
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
