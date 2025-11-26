"""Main HITL Agent - simplified single agent with approval workflow."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .tools import (
    request_human_approval,
    process_human_decision,
    submit_rectified_output,
    execute_approved_action,
)
from .prompts import ROOT_AGENT_PROMPT


# Default model - can be overridden via environment or config
MODEL_ID = "gemini-2.0-flash"


# Single agent with all HITL tools
root_agent = Agent(
    name="hitl_agent",
    model=MODEL_ID,
    description="Human-in-the-Loop agent that creates content and asks for approval before executing",
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        FunctionTool(func=request_human_approval),
        FunctionTool(func=process_human_decision),
        FunctionTool(func=submit_rectified_output),
        FunctionTool(func=execute_approved_action),
    ],
)
