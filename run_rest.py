"""REST API for HITL Agent with VertexAI Memory Bank.

No WebSocket required - uses standard HTTP POST endpoints.

Usage:
    uv run python run_rest.py
    
Then call:
    POST /chat - Send message
    POST /end-session/{user_id}/{session_id} - End and save to memory
    GET /memories/{user_id} - Retrieve user's memories
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from google.adk.runners import Runner
from google.genai import types

from hitl_agent.agent import root_agent
from hitl_agent.services import get_session_service, get_memory_service


load_dotenv()


# Global services
session_service = None
memory_service = None
runner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global session_service, memory_service, runner
    
    session_service = get_session_service()
    memory_service = get_memory_service()
    
    runner = Runner(
        agent=root_agent,
        app_name="hitl_trip_planner",
        session_service=session_service,
        memory_service=memory_service,
    )
    
    print("\n" + "="*60)
    print("HITL Agent REST API")
    print("="*60)
    print(f"Session Service: {type(session_service).__name__}")
    print(f"Memory Service: {type(memory_service).__name__}")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /chat              - Send message to agent")
    print("  POST /end-session/{user_id}/{session_id} - Save to memory")
    print("  GET  /memories/{user_id} - Get user's memories")
    print("="*60 + "\n")
    
    yield
    
    print("\nShutting down...")


app = FastAPI(
    title="HITL Agent API",
    description="Human-in-the-Loop Agent with VertexAI Memory Bank",
    lifespan=lifespan,
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str

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

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the HITL agent.
    
    - First call: omit session_id to create a new session
    - Subsequent calls: include session_id to continue conversation
    """
    try:
        # Create or get session
        if request.session_id:
            try:
                session = await session_service.get_session(
                    app_name="hitl_trip_planner",
                    user_id=request.user_id,
                    session_id=request.session_id,
                )
            except Exception:
                # Session not found, create new
                session = await session_service.create_session(
                    app_name="hitl_trip_planner",
                    user_id=request.user_id,
                )
        else:
            session = await session_service.create_session(
                app_name="hitl_trip_planner",
                user_id=request.user_id,
            )
        
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
            app_name="hitl_trip_planner",
            user_id=request.user_id,
            session_id=session.id,
        )
        
        state = session.state or {}
        awaiting_approval = state.get("awaiting_approval", False)
        trip_finalized = state.get("trip_finalized", False)
        
        # Auto-save to memory on approval
        if state.get("approved"):
            try:
                await memory_service.add_session_to_memory(session)
                print(f"Session {session.id} saved to memory bank")
            except Exception as e:
                print(f"Error saving to memory: {e}")
        
        return ChatResponse(
            session_id=session.id,
            response=response_text or "No response generated.",
            awaiting_approval=awaiting_approval,
            trip_finalized=trip_finalized,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/end-session/{user_id}/{session_id}")
async def end_session(user_id: str, session_id: str):
    """
    End a session and save it to Memory Bank.
    
    Call this when the user is done with the conversation
    to persist the session to long-term memory.
    """
    try:
        session = await session_service.get_session(
            app_name="hitl_trip_planner",
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


@app.get("/memories/{user_id}", response_model=MemoriesResponse)
async def get_memories(user_id: str, query: str = "trip plans and preferences"):
    """
    Retrieve memories for a user from Memory Bank.
    
    Args:
        user_id: The user ID to retrieve memories for
        query: Search query for semantic similarity (default: "trip plans and preferences")
    """
    try:
        memory_response = await memory_service.search_memory(
            app_name="hitl_trip_planner",
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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# Main
# ============================================================================

def main():
    port = int(os.getenv("PORT", 8080))
    print(f"Starting HITL Agent REST API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

