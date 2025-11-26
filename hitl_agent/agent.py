"""HITL Agent with turn-based approval flow.

Flow:
1. User requests trip → capture_request → proposal_agent generates
2. present_proposal outputs proposal and asks for approve/reject
3. User responds → root_agent handles:
   - "approve" → process_approval → done
   - "reject: feedback" → process_rejection → iterative_agent fixes → present_revised
4. Loop until approved
"""

from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from .tools import (
    capture_request,
    generate_route,
    generate_accommodation,
    generate_activities,
    present_proposal,
    process_approval,
    process_rejection,
    fix_route,
    fix_accommodation,
    fix_activities,
    present_revised_proposal,
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
# PROPOSAL SUB-AGENTS (SequentialAgent)
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
    tools=[FunctionTool(func=present_proposal)],
)


# ============================================================================
# PROPOSAL AGENT (SequentialAgent)
# ============================================================================

proposal_agent = SequentialAgent(
    name="proposal_agent",
    description="Generates complete proposal sequentially",
    sub_agents=[
        route_agent,
        accommodation_agent,
        activity_agent,
        finalizer_agent,
    ],
)


# ============================================================================
# CORRECTION SUB-AGENTS (for iterative_agent)
# ============================================================================

route_fixer = LlmAgent(
    name="route_fixer",
    model=MODEL_ID,
    instruction=ROUTE_PROMPT + "\n\nYou are FIXING the route. Read state['feedback'] for what to change.",
    tools=[FunctionTool(func=fix_route)],
)

accommodation_fixer = LlmAgent(
    name="accommodation_fixer",
    model=MODEL_ID,
    instruction=ACCOMMODATION_PROMPT + "\n\nYou are FIXING accommodations. Read state['feedback'] for what to change.",
    tools=[FunctionTool(func=fix_accommodation)],
)

activity_fixer = LlmAgent(
    name="activity_fixer",
    model=MODEL_ID,
    instruction=ACTIVITY_PROMPT + "\n\nYou are FIXING activities. Read state['feedback'] for what to change.",
    tools=[FunctionTool(func=fix_activities)],
)


# ============================================================================
# ITERATIVE AGENT (handles corrections)
# ============================================================================

iterative_agent = Agent(
    name="iterative_agent",
    model=MODEL_ID,
    description="Fixes specific parts based on feedback and re-presents proposal",
    instruction=ITERATIVE_PROMPT,
    tools=[FunctionTool(func=present_revised_proposal)],
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
    description="Orchestrates trip planning with human approval",
    instruction=ROOT_PROMPT,
    tools=[
        FunctionTool(func=capture_request),
        FunctionTool(func=process_approval),
        FunctionTool(func=process_rejection),
    ],
    sub_agents=[
        proposal_agent,
        iterative_agent,
    ],
)
