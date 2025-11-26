"""HITL Agent with SequentialAgent + Iterative correction.

Architecture:
1. Root agent captures request, delegates to proposal_agent
2. SequentialAgent builds proposal, asks for approval
3. If rejected: iterative_agent routes to specific sub-agent to fix
4. Fixed content goes back for approval
"""

from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from .tools import (
    capture_request,
    generate_route,
    generate_accommodation,
    generate_activities,
    finalize_proposal,
    store_feedback,
    fix_route,
    fix_accommodation,
    fix_activities,
    resubmit_proposal,
)
from .prompts import (
    ROOT_PROMPT,
    ROUTE_PROMPT,
    ACCOMMODATION_PROMPT,
    ACTIVITY_PROMPT,
    FINALIZER_PROMPT,
    ITERATIVE_PROMPT,
)


MODEL_ID = "gemini-2.0-flash"


# ============================================================================
# SUB-AGENTS FOR INITIAL PROPOSAL (SequentialAgent)
# ============================================================================

route_agent = LlmAgent(
    name="route_agent",
    model=MODEL_ID,
    instruction=ROUTE_PROMPT,
    tools=[FunctionTool(func=generate_route)],
)

accommodation_agent = LlmAgent(
    name="accommodation_agent",
    model=MODEL_ID,
    instruction=ACCOMMODATION_PROMPT,
    tools=[FunctionTool(func=generate_accommodation)],
)

activity_agent = LlmAgent(
    name="activity_agent",
    model=MODEL_ID,
    instruction=ACTIVITY_PROMPT,
    tools=[FunctionTool(func=generate_activities)],
)

finalizer_agent = LlmAgent(
    name="finalizer_agent",
    model=MODEL_ID,
    instruction=FINALIZER_PROMPT,
    tools=[
        FunctionTool(func=finalize_proposal, require_confirmation=True),
    ],
)


# ============================================================================
# PROPOSAL AGENT (SequentialAgent)
# ============================================================================

proposal_agent = SequentialAgent(
    name="proposal_agent",
    description="Runs sub-agents sequentially to build complete proposal",
    sub_agents=[
        route_agent,
        accommodation_agent,
        activity_agent,
        finalizer_agent,
    ],
)


# ============================================================================
# CORRECTION SUB-AGENTS (for iterative_agent)
# These are separate instances that fix specific parts
# ============================================================================

route_fixer = LlmAgent(
    name="route_fixer",
    model=MODEL_ID,
    instruction=ROUTE_PROMPT + "\n\nYou are FIXING the route based on feedback in state['feedback']. Read the feedback and improve accordingly.",
    tools=[FunctionTool(func=fix_route)],
)

accommodation_fixer = LlmAgent(
    name="accommodation_fixer",
    model=MODEL_ID,
    instruction=ACCOMMODATION_PROMPT + "\n\nYou are FIXING accommodations based on feedback in state['feedback']. Read the feedback and improve accordingly.",
    tools=[FunctionTool(func=fix_accommodation)],
)

activity_fixer = LlmAgent(
    name="activity_fixer",
    model=MODEL_ID,
    instruction=ACTIVITY_PROMPT + "\n\nYou are FIXING activities based on feedback in state['feedback']. Read the feedback and improve accordingly.",
    tools=[FunctionTool(func=fix_activities)],
)


# ============================================================================
# ITERATIVE AGENT (handles rejection and routes to correct fixer)
# ============================================================================

iterative_agent = Agent(
    name="iterative_agent",
    model=MODEL_ID,
    description="Analyzes rejection feedback and routes to specific fixer agent",
    instruction=ITERATIVE_PROMPT,
    tools=[
        FunctionTool(func=store_feedback),
        FunctionTool(func=resubmit_proposal, require_confirmation=True),
    ],
    sub_agents=[
        route_fixer,
        accommodation_fixer,
        activity_fixer,
    ],
)


# ============================================================================
# ROOT AGENT
# ============================================================================

root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Orchestrates proposal generation, approval, and iterative correction",
    instruction=ROOT_PROMPT,
    tools=[
        FunctionTool(func=capture_request),
    ],
    sub_agents=[
        proposal_agent,
        iterative_agent,
    ],
)
