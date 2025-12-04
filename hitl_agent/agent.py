"""HITL Agent with turn-based approval flow.

Flow:
1. User requests trip → capture_request → proposal_agent generates
2. present_proposal outputs full proposal
3. User: approve → process_approval → done
4. User: reject → process_rejection → iterative_agent fixes AND presents revised
"""

from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool, load_memory
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

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
    show_final_plan,
    recall_trip_info,
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
# CALLBACK: Auto-save session to memory after each agent turn
# This is the recommended approach from ADK docs
# Reference: https://google.github.io/adk-docs/sessions/memory/
# ============================================================================

async def auto_save_to_memory_callback(callback_context):
    """
    Automatically save session to Memory Bank after each agent turn.
    Memory Bank extracts meaningful information from conversation events.
    """
    try:
        memory_service = callback_context._invocation_context.memory_service
        session = callback_context._invocation_context.session
        
        if memory_service and session:
            await memory_service.add_session_to_memory(session)
            print(f"[Memory Callback] Session {session.id} saved to Memory Bank")
    except Exception as e:
        print(f"[Memory Callback] Error saving to memory: {e}")


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
# ITERATIVE AGENT - has ALL fix tools directly, no sub-agents
# This ensures it can fix AND present revised proposal in sequence
# ============================================================================

iterative_agent = LlmAgent(
    name="iterative_agent",
    model=MODEL_ID,
    description="Fixes specific parts and presents revised proposal",
    instruction=ITERATIVE_PROMPT,
    tools=[
        FunctionTool(func=fix_route),
        FunctionTool(func=fix_accommodation),
        FunctionTool(func=fix_activities),
        FunctionTool(func=present_revised_proposal),
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
        PreloadMemoryTool(),  # Auto-loads memory at start of each turn
        FunctionTool(func=capture_request),
        FunctionTool(func=process_approval),
        FunctionTool(func=process_rejection),
        FunctionTool(func=show_final_plan),
        FunctionTool(func=recall_trip_info),
        load_memory,  # Manual memory retrieval tool
    ],
    sub_agents=[
        proposal_agent,
        iterative_agent,
    ],
    after_agent_callback=auto_save_to_memory_callback,  # Auto-save after each turn
)
