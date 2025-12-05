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
from google.adk.tools import FunctionTool
from google.genai import types

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

# Configure to prefer tool usage
generate_config = types.GenerateContentConfig(
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",  # Force the model to use tools
        )
    )
)

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
    ],
    generate_content_config=generate_config,
)

# Export as root_agent for the executor
root_agent = iterative_agent
