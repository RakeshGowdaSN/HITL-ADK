"""Iterative Agent - LlmAgent that fixes proposals based on feedback."""

import os
import sys

# Ensure script directory is in path
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, load_memory

from tools import (
    fix_route,
    fix_accommodation,
    fix_activities,
    present_revised_proposal,
)
from prompts import ITERATIVE_PROMPT


MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-pro")


# ============================================================================
# ITERATIVE AGENT
# Has all fix tools directly (no sub-agents) to ensure it can fix AND present
# revised proposal in the same turn
# ============================================================================

iterative_agent = LlmAgent(
    name="iterative_agent",
    model=MODEL_ID,
    description="Fixes specific parts of trip proposal based on user feedback and presents revised version",
    instruction=ITERATIVE_PROMPT,
    tools=[
        FunctionTool(func=fix_route),
        FunctionTool(func=fix_accommodation),
        FunctionTool(func=fix_activities),
        FunctionTool(func=present_revised_proposal),
        load_memory,  # Can recall user preferences to better address feedback
    ],
)

# Export as root_agent for the executor
root_agent = iterative_agent

