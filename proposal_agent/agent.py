"""Proposal Agent - SequentialAgent that generates trip proposals."""

import os
import sys

# Ensure script directory is in path
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool, load_memory

from tools import (
    generate_route,
    generate_accommodation,
    generate_activities,
    present_proposal,
)
from prompts import (
    ROUTE_PROMPT,
    ACCOMMODATION_PROMPT,
    ACTIVITY_PROMPT,
    FINALIZER_PROMPT,
)


MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-pro")


# ============================================================================
# PROPOSAL SUB-AGENTS
# ============================================================================

route_agent = LlmAgent(
    name="route_agent",
    model=MODEL_ID,
    instruction=ROUTE_PROMPT,
    tools=[
        FunctionTool(func=generate_route),
        load_memory,  # Can recall user's travel preferences
    ],
)

accommodation_agent = LlmAgent(
    name="accommodation_agent",
    model=MODEL_ID,
    instruction=ACCOMMODATION_PROMPT,
    tools=[
        FunctionTool(func=generate_accommodation),
        load_memory,  # Can recall user's hotel preferences
    ],
)

activity_agent = LlmAgent(
    name="activity_agent",
    model=MODEL_ID,
    instruction=ACTIVITY_PROMPT,
    tools=[
        FunctionTool(func=generate_activities),
        load_memory,  # Can recall user's activity preferences
    ],
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
    description="Generates complete trip proposal by running route, accommodation, activity, and finalizer agents sequentially",
    sub_agents=[
        route_agent,
        accommodation_agent,
        activity_agent,
        finalizer_agent,
    ],
)

# Export as root_agent for the executor
root_agent = proposal_agent

