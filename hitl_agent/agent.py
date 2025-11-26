"""HITL Agent with SequentialAgent that works properly.

Architecture:
1. Root agent receives user request and stores in state
2. Delegates to proposal_agent (SequentialAgent)
3. Sub-agents read from state and generate content
4. Final approval step with require_confirmation=True
"""

from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from .tools import (
    capture_request,
    generate_route,
    generate_accommodation,
    generate_activities,
    finalize_proposal,
)
from .prompts import (
    ROOT_PROMPT,
    ROUTE_PROMPT,
    ACCOMMODATION_PROMPT,
    ACTIVITY_PROMPT,
    FINALIZER_PROMPT,
)


MODEL_ID = "gemini-2.0-flash"


# ============================================================================
# SUB-AGENTS FOR SEQUENTIAL EXECUTION
# Each reads from state and generates its part
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
        # This pauses for human approval
        FunctionTool(func=finalize_proposal, require_confirmation=True),
    ],
)


# ============================================================================
# PROPOSAL AGENT (SequentialAgent)
# ============================================================================

proposal_agent = SequentialAgent(
    name="proposal_agent",
    description="Runs sub-agents in sequence to build complete proposal",
    sub_agents=[
        route_agent,
        accommodation_agent,
        activity_agent,
        finalizer_agent,
    ],
)


# ============================================================================
# ROOT AGENT
# ============================================================================

root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Captures user request, runs proposal sequence, handles approval/rejection",
    instruction=ROOT_PROMPT,
    tools=[
        FunctionTool(func=capture_request),
    ],
    sub_agents=[
        proposal_agent,
    ],
)
