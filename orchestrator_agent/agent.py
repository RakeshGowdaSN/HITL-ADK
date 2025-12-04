"""Orchestrator Agent - A2A Client that coordinates Proposal and Iterative agents."""

import os
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools import FunctionTool, load_memory

from .tools import (
    capture_request,
    get_delegation_message,
    process_approval,
    process_rejection,
    show_final_plan,
    recall_trip_info,
    store_proposal_response,
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
# FACTORY FUNCTION - Creates agents at runtime to avoid client closure issues
# ============================================================================

def create_remote_agents():
    """
    Create fresh RemoteA2aAgent instances.
    Called at runtime to prevent 'client has been closed' errors.
    """
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
    
    return proposal_agent, iterative_agent


def create_root_agent():
    """
    Factory function to create the root agent with fresh RemoteA2aAgent instances.
    This prevents the 'client has been closed' error by creating agents at runtime
    instead of at module import time.
    """
    proposal_agent, iterative_agent = create_remote_agents()

    return Agent(
        name="hitl_orchestrator",
        model=MODEL_ID,
        description="Orchestrates trip planning with human approval using remote A2A agents",
        instruction=ROOT_PROMPT,
        tools=[
            FunctionTool(func=capture_request),
            FunctionTool(func=get_delegation_message),
            FunctionTool(func=store_proposal_response),
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


# ============================================================================
# SINGLETON PATTERN - For contexts that need a cached instance
# ============================================================================

_root_agent_instance = None


def get_root_agent():
    """
    Get or create the root agent singleton.
    Use this when you need a cached instance (e.g., for repeated calls).
    For fresh instances in async contexts, use create_root_agent() directly.
    """
    global _root_agent_instance
    if _root_agent_instance is None:
        _root_agent_instance = create_root_agent()
    return _root_agent_instance


# For backwards compatibility - but prefer using create_root_agent() or get_root_agent()
# This creates the agent at import time which may cause issues in some contexts
root_agent = None  # Lazy - will be created on first access via get_root_agent()
