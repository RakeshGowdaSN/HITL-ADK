"""REST API for Orchestrator Agent with VertexAI Memory Bank.

Exposes the orchestrator agent as FastAPI endpoints.

Usage:
    cd orchestrator_agent
    
    # Option 1: Run with uvicorn (recommended, supports auto-reload)
    uvicorn run_rest:app --reload --host 0.0.0.0 --port 8080
    
    # Option 2: Run directly
    python run_rest.py
    
Endpoints:
    POST /chat - Send message to agent
    POST /end-session/{user_id}/{session_id} - End and save to memory
    GET /memories/{user_id} - Retrieve user's memories
    GET /docs - Swagger UI
"""

import os
import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Ensure we can import from current directory
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from google.adk.runners import Runner
from google.genai import types
from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import VertexAiSessionService

from agent import create_root_agent


# CRITICAL: Use the SAME app_name across ALL agents for shared memory!
# This must match what proposal_agent and iterative_agent use
APP_NAME = "hitl_trip_planner"

# Get Agent Engine ID
ENGINE_ID = os.getenv("AGENT_ENGINE_ID")


# Global services
session_service = None
memory_service = None
runner = None


def get_services():
    """Initialize VertexAI services."""
    if not ENGINE_ID:
        raise ValueError("AGENT_ENGINE_ID is required. Set it in your .env file.")
    
    session_svc = VertexAiSessionService(agent_engine_id=ENGINE_ID)
    memory_svc = VertexAiMemoryBankService(agent_engine_id=ENGINE_ID)
    
    return session_svc, memory_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global session_service, memory_service, runner
    
    session_service, memory_service = get_services()
    
    # Create fresh agent instance
    root_agent = create_root_agent()
    
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service,
    )
    
    print("\n" + "="*60)
    print("ORCHESTRATOR AGENT - REST API")
    print("="*60)
    print(f"Agent Engine ID: {ENGINE_ID}")
    print(f"Session Service: {type(session_service).__name__}")
    print(f"Memory Service: {type(memory_service).__name__}")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /chat              - Send message to agent")
    print("  POST /end-session/{user_id}/{session_id} - Save to memory")
    print("  GET  /memories/{user_id} - Get user's memories")
    print("  GET  /docs              - Swagger UI")
    print("="*60 + "\n")
    
    yield
    
    print("\nShutting down...")


app = FastAPI(
    title="Orchestrator Agent API",
    description="Human-in-the-Loop Orchestrator Agent with VertexAI Memory Bank and Remote A2A Sub-agents",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": None,
                "message": "Plan a 5 day trip to Kerala from Bangalore"
            }
        }


class ChatResponse(BaseModel):
    session_id: str
    response: str
    awaiting_approval: bool = False
    trip_finalized: bool = False


class MemoriesResponse(BaseModel):
    user_id: str
    count: int
    memories: list[str]


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Send a message to the Orchestrator Agent.
    
    The orchestrator coordinates with remote Proposal and Iterative agents
    deployed on Cloud Run.
    
    **Flow:**
    1. First call: omit session_id to create a new session
    2. Request a trip: "Plan a 5 day trip to Kerala from Bangalore"
    3. Review proposal and approve: "approve" or reject with feedback
    4. On rejection: provide feedback like "I want budget hotels instead"
    """
    try:
        # Create or get session
        if request.session_id:
            try:
                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=request.user_id,
                    session_id=request.session_id,
                )
            except Exception:
                # Session not found, create new
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=request.user_id,
                )
        else:
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=request.user_id,
            )
        
        print(f"[Chat] User: {request.user_id}, Session: {session.id}")
        print(f"[Chat] Message: {request.message[:100]}...")
        
        # Run agent
        content = types.Content(
            role="user",
            parts=[types.Part(text=request.message)]
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text
        
        # Get updated session state
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=request.user_id,
            session_id=session.id,
        )
        
        state = session.state or {}
        awaiting_approval = state.get("awaiting_approval", False)
        trip_finalized = state.get("trip_finalized", False)
        
        # Note: Memory is automatically saved via after_agent_callback in the agent
        # The callback extracts info from session events (conversation history)
        # See: https://google.github.io/adk-docs/sessions/memory/
        
        return ChatResponse(
            session_id=session.id,
            response=response_text or "No response generated.",
            awaiting_approval=awaiting_approval,
            trip_finalized=trip_finalized,
        )
        
    except Exception as e:
        print(f"[Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/end-session/{user_id}/{session_id}", tags=["Session"])
async def end_session(user_id: str, session_id: str):
    """
    End a session and save it to Memory Bank.
    
    Call this when the user is done with the conversation
    to persist the session to long-term memory.
    """
    try:
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        
        await memory_service.add_session_to_memory(session)
        
        return {
            "status": "success",
            "message": f"Session {session_id} saved to Memory Bank",
            "user_id": user_id,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{user_id}", response_model=MemoriesResponse, tags=["Memory"])
async def get_memories(user_id: str, query: str = "trip plans and preferences"):
    """
    Retrieve memories for a user from Memory Bank.
    
    Args:
        user_id: The user ID to retrieve memories for
        query: Search query for semantic similarity
    """
    try:
        memory_response = await memory_service.search_memory(
            app_name=APP_NAME,
            user_id=user_id,
            query=query,
        )
        
        # Extract memories from response
        memory_list = getattr(memory_response, 'memories', []) or []
        
        # Extract fact text from each memory
        facts = []
        for mem in memory_list:
            if hasattr(mem, 'fact'):
                facts.append(mem.fact)
            elif isinstance(mem, dict) and 'fact' in mem:
                facts.append(mem['fact'])
            else:
                facts.append(str(mem))
        
        return MemoriesResponse(
            user_id=user_id,
            count=len(facts),
            memories=facts,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{user_id}", tags=["Session"])
async def list_sessions(user_id: str):
    """
    List all sessions for a user.
    """
    try:
        sessions = await session_service.list_sessions(
            app_name=APP_NAME,
            user_id=user_id,
        )
        
        return {
            "user_id": user_id,
            "count": len(sessions) if sessions else 0,
            "sessions": [
                {
                    "id": s.id,
                    "state": s.state,
                }
                for s in (sessions or [])
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_engine_id": ENGINE_ID,
        "app_name": APP_NAME,
    }


# ============================================================================
# Main
# ============================================================================

def main():
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Orchestrator Agent REST API on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

