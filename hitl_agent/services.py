"""VertexAI Session and Memory Services configuration."""

import os
from typing import Optional


def _should_use_vertex_services() -> bool:
    return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"


def _create_vertex_services_condition(agent_engine_id: Optional[str]):
    use_vertex = _should_use_vertex_services()
    engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")
    return use_vertex and engine_id


def get_session_service(agent_engine_id: Optional[str] = None):
    """
    Get configured VertexAI Session Service or fall back to in-memory.
    """
    if _create_vertex_services_condition(agent_engine_id):
        from google.adk.sessions import VertexAiSessionService

        engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")
        print(f"Using VertexAiSessionService with Agent Engine: {engine_id}")
        return VertexAiSessionService(agent_engine_id=engine_id)

    from google.adk.sessions import InMemorySessionService
    print("Using InMemorySessionService (local testing mode)")
    return InMemorySessionService()


def get_memory_service(agent_engine_id: Optional[str] = None):
    """
    Get configured VertexAI Memory Bank Service or fall back to in-memory.
    """
    if _create_vertex_services_condition(agent_engine_id):
        from google.adk.memory import VertexAiMemoryBankService

        engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")
        print(f"Using VertexAiMemoryBankService with Agent Engine: {engine_id}")
        return VertexAiMemoryBankService(agent_engine_id=engine_id)

    from google.adk.memory import InMemoryMemoryService
    print("Using InMemoryMemoryService (local testing mode)")
    return InMemoryMemoryService()


def create_agent_engine(
    display_name: str = "HITL Agent Engine",
    description: str = "Agent Engine for HITL workflow",
):
    """
    Create a new Agent Engine instance using VertexAI SDK.
    This is needed before using VertexAiSessionService and VertexAiMemoryBankService.

    Requires service account credentials (GOOGLE_APPLICATION_CREDENTIALS) and
    GOOGLE_CLOUD_PROJECT. API keys are not supported for Agent Engine creation.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT is required. "
            "Set it in your .env file along with GOOGLE_APPLICATION_CREDENTIALS."
        )

    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=project, location=location)

    agent_engine = agent_engines.create(
        display_name=display_name,
        description=description,
    )

    engine_id = agent_engine.name.split("/")[-1]

    print(f"Created Agent Engine with ID: {engine_id}")
    print(f"Add this to your .env file: AGENT_ENGINE_ID={engine_id}")

    return engine_id


async def setup_services(agent_engine_id: Optional[str] = None):
    """
    Setup both session and memory services.
    
    Args:
        agent_engine_id: Optional Agent Engine ID
    
    Returns:
        Tuple of (session_service, memory_service)
    """
    session_service = get_session_service(agent_engine_id)
    memory_service = get_memory_service(agent_engine_id)
    
    return session_service, memory_service

