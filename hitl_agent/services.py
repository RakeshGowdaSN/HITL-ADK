"""VertexAI Session and Memory Services configuration."""

import os
from typing import Optional


def get_session_service(agent_engine_id: Optional[str] = None):
    """
    Get configured VertexAI Session Service.
    
    For Express Mode: Uses API key from environment
    For Full VertexAI: Uses project/location from environment
    
    Args:
        agent_engine_id: Optional Agent Engine ID (uses env var if not provided)
    
    Returns:
        Configured session service (VertexAiSessionService or InMemorySessionService for local)
    """
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
    engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")
    
    if use_vertex and engine_id:
        # Use VertexAI Session Service
        from google.adk.sessions import VertexAiSessionService
        
        print(f"🔧 Using VertexAiSessionService with Agent Engine: {engine_id}")
        return VertexAiSessionService(agent_engine_id=engine_id)
    else:
        # Fall back to in-memory for local testing
        from google.adk.sessions import InMemorySessionService
        
        print("🔧 Using InMemorySessionService (local testing mode)")
        return InMemorySessionService()


def get_memory_service(agent_engine_id: Optional[str] = None):
    """
    Get configured VertexAI Memory Bank Service.
    
    For Express Mode: Uses API key from environment
    For Full VertexAI: Uses project/location from environment
    
    Args:
        agent_engine_id: Optional Agent Engine ID (uses env var if not provided)
    
    Returns:
        Configured memory service (VertexAiMemoryBankService or InMemoryMemoryService for local)
    """
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
    engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")
    
    if use_vertex and engine_id:
        # Use VertexAI Memory Bank Service
        from google.adk.memory import VertexAiMemoryBankService
        
        print(f"🔧 Using VertexAiMemoryBankService with Agent Engine: {engine_id}")
        return VertexAiMemoryBankService(agent_engine_id=engine_id)
    else:
        # Fall back to in-memory for local testing
        from google.adk.memory import InMemoryMemoryService
        
        print("🔧 Using InMemoryMemoryService (local testing mode)")
        return InMemoryMemoryService()


def create_agent_engine(display_name: str = "HITL Agent Engine", description: str = "Agent Engine for HITL workflow"):
    """
    Create a new Agent Engine instance using VertexAI SDK.
    This is needed before using VertexAiSessionService and VertexAiMemoryBankService.
    
    Args:
        display_name: Display name for the agent engine
        description: Description of the agent engine
    
    Returns:
        The created agent engine ID
    """
    import vertexai
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    # Initialize Vertex AI client
    client = vertexai.Client(api_key=api_key)
    
    # Create agent engine
    agent_engine = client.agent_engines.create(
        config={
            "display_name": display_name,
            "description": description,
        }
    )
    
    # Extract the ID from the resource name
    engine_id = agent_engine.api_resource.name.split('/')[-1]
    
    print(f"✅ Created Agent Engine with ID: {engine_id}")
    print(f"   Add this to your .env file: AGENT_ENGINE_ID={engine_id}")
    
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

