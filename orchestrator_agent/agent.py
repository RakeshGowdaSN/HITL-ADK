"""Orchestrator Agent - A2A Client that coordinates Proposal and Iterative agents."""

import os
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools import FunctionTool, load_memory

from .tools import (
    capture_request,
    process_approval,
    process_rejection,
    show_final_plan,
    recall_trip_info,
)
from .prompts import ROOT_PROMPT


MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-pro")

# Remote A2A Agent URLs (Cloud Run deployments)
PROPOSAL_AGENT_URL = os.getenv(
    "PROPOSAL_AGENT_URL",
    "https://proposal-agent-service.us-east1.run.app/.well-known/agent.json"
)
ITERATIVE_AGENT_URL = os.getenv(
    "ITERATIVE_AGENT_URL", 
    "https://iterative-agent-service.us-east1.run.app/.well-known/agent.json"
)


# ============================================================================
# REMOTE A2A AGENTS (deployed on Cloud Run)
# ============================================================================

proposal_agent = RemoteA2aAgent(
    name="proposal_agent",
    description="Generates complete trip proposal sequentially (route, accommodation, activities)",
    agent_card=PROPOSAL_AGENT_URL,
    timeout=3600,
)

iterative_agent = RemoteA2aAgent(
    name="iterative_agent",
    description="Fixes specific parts of proposal based on user feedback and presents revised version",
    agent_card=ITERATIVE_AGENT_URL,
    timeout=3600,
)


# ============================================================================
# ROOT AGENT (Orchestrator)
# ============================================================================

root_agent = Agent(
    name="hitl_orchestrator",
    model=MODEL_ID,
    description="Orchestrates trip planning with human approval using remote A2A agents",
    instruction=ROOT_PROMPT,
    tools=[
        FunctionTool(func=capture_request),
        FunctionTool(func=process_approval),
        FunctionTool(func=process_rejection),
        FunctionTool(func=show_final_plan),
        FunctionTool(func=recall_trip_info),
        load_memory,  # ADK built-in tool to retrieve memories from Memory Bank
    ],
    sub_agents=[
        proposal_agent,
        iterative_agent,
    ],
)

