"""Web Interface for Orchestrator Agent with VertexAI Memory Bank.

A modern chat UI with WebSocket for real-time communication.

Usage:
    cd orchestrator_agent
    
    # Option 1: Run with uvicorn (recommended, supports auto-reload)
    uvicorn run_web:app --reload --host 0.0.0.0 --port 8080
    
    # Option 2: Run directly
    python run_web.py
    
Then open http://localhost:8080 in your browser.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
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
# This must match proposal_agent and iterative_agent
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
    print("ORCHESTRATOR AGENT - Web Interface")
    print("="*60)
    print(f"Agent Engine ID: {ENGINE_ID}")
    print(f"Session Service: {type(session_service).__name__}")
    print(f"Memory Service: {type(memory_service).__name__}")
    print("="*60 + "\n")
    
    yield
    
    print("\nShutting down...")


app = FastAPI(lifespan=lifespan)


# Store active sessions
active_sessions = {}


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Orchestrator Agent</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a24;
            --accent-primary: #6366f1;
            --accent-secondary: #818cf8;
            --accent-glow: rgba(99, 102, 241, 0.3);
            --success: #10b981;
            --warning: #f59e0b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border: #2d2d3a;
            --border-light: #3d3d4a;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Space Grotesk', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(ellipse at top, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
                radial-gradient(ellipse at bottom right, rgba(16, 185, 129, 0.05) 0%, transparent 50%);
        }
        
        header {
            padding: 1.25rem 2rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-secondary);
            backdrop-filter: blur(10px);
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
        }
        
        header h1 { 
            font-size: 1.1rem; 
            font-weight: 600;
            background: linear-gradient(90deg, var(--text-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        #session-info { 
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem; 
            color: var(--text-muted);
            background: var(--bg-tertiary);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            border: 1px solid var(--border);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }
        
        .message {
            max-width: 75%;
            padding: 1rem 1.25rem;
            border-radius: 12px;
            white-space: pre-wrap;
            line-height: 1.7;
            font-size: 0.95rem;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user {
            align-self: flex-end;
            background: linear-gradient(135deg, var(--accent-primary), #4f46e5);
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .agent {
            align-self: flex-start;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-bottom-left-radius: 4px;
        }
        
        .system {
            align-self: center;
            background: transparent;
            border: 1px dashed var(--border);
            color: var(--text-muted);
            font-size: 0.85rem;
            padding: 0.75rem 1rem;
            border-radius: 8px;
        }
        
        .system.success {
            border-color: var(--success);
            color: var(--success);
        }
        
        .system.warning {
            border-color: var(--warning);
            color: var(--warning);
        }
        
        #input-container {
            padding: 1.25rem 2rem;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 1rem;
            background: var(--bg-secondary);
        }
        
        #message-input {
            flex: 1;
            padding: 1rem 1.25rem;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.95rem;
            transition: all 0.2s;
        }
        
        #message-input:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        
        #message-input::placeholder {
            color: var(--text-muted);
        }
        
        button {
            padding: 1rem 1.75rem;
            border: none;
            border-radius: 12px;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        #send-btn {
            background: linear-gradient(135deg, var(--accent-primary), #4f46e5);
            color: white;
        }
        
        #send-btn:hover:not(:disabled) { 
            transform: translateY(-1px);
            box-shadow: 0 4px 12px var(--accent-glow);
        }
        
        #send-btn:disabled { 
            opacity: 0.5; 
            cursor: not-allowed; 
        }
        
        #new-session { 
            background: transparent; 
            border: 1px solid var(--border); 
            color: var(--text-secondary);
        }
        
        #new-session:hover {
            border-color: var(--accent-primary);
            color: var(--accent-secondary);
        }
        
        .quick-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            padding: 0.5rem 2rem 1rem;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }
        
        .quick-btn {
            padding: 0.5rem 1rem;
            font-size: 0.8rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            border-radius: 20px;
        }
        
        .quick-btn:hover {
            border-color: var(--accent-primary);
            color: var(--accent-secondary);
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { 
            background: var(--border); 
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--border-light); }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            <div class="logo-icon">O</div>
            <h1>Orchestrator Agent</h1>
        </div>
        <div class="header-right">
            <div class="status-dot"></div>
            <span id="session-info">Connecting...</span>
            <button id="new-session" onclick="newSession()">New Session</button>
        </div>
    </header>
    
    <div id="chat-container"></div>
    
    <div class="quick-actions">
        <button class="quick-btn" onclick="sendQuick('Plan a 5 day trip to Kerala from Bangalore')">Kerala Trip</button>
        <button class="quick-btn" onclick="sendQuick('approve')">Approve</button>
        <button class="quick-btn" onclick="sendQuick('Show my trip plan')">Show Plan</button>
        <button class="quick-btn" onclick="sendQuick('What trips have I planned before?')">Past Trips</button>
    </div>
    
    <div id="input-container">
        <input type="text" id="message-input" placeholder="Type your message... (e.g., Plan a trip to Goa)" onkeypress="handleKeyPress(event)">
        <button id="send-btn" onclick="sendMessage()">Send</button>
    </div>
    
    <script>
        let ws;
        let sessionId = localStorage.getItem('orchestrator_sessionId');
        let userId = localStorage.getItem('orchestrator_userId') || 'user_' + Math.random().toString(36).substr(2, 8);
        localStorage.setItem('orchestrator_userId', userId);
        
        function connect() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/${userId}` + (sessionId ? `?session_id=${sessionId}` : '');
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                addMessage('Connected to Orchestrator Agent', 'system');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'session') {
                    sessionId = data.session_id;
                    localStorage.setItem('orchestrator_sessionId', sessionId);
                    document.getElementById('session-info').textContent = 
                        `Session: ${sessionId.substr(0, 8)}... | User: ${userId}`;
                } else if (data.type === 'response') {
                    addMessage(data.text, 'agent');
                    document.getElementById('send-btn').disabled = false;
                } else if (data.type === 'memory_loaded') {
                    addMessage(`Loaded ${data.count} memories from previous sessions`, 'system success');
                } else if (data.type === 'error') {
                    addMessage(`Error: ${data.text}`, 'system warning');
                    document.getElementById('send-btn').disabled = false;
                }
            };
            
            ws.onclose = () => {
                addMessage('Disconnected. Reconnecting...', 'system warning');
                setTimeout(connect, 2000);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        function addMessage(text, type) {
            const container = document.getElementById('chat-container');
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.textContent = text;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }
        
        function sendMessage() {
            const input = document.getElementById('message-input');
            const text = input.value.trim();
            if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
            
            addMessage(text, 'user');
            ws.send(JSON.stringify({ text: text }));
            input.value = '';
            document.getElementById('send-btn').disabled = true;
        }
        
        function sendQuick(text) {
            if (!ws || ws.readyState !== WebSocket.OPEN) return;
            addMessage(text, 'user');
            ws.send(JSON.stringify({ text: text }));
            document.getElementById('send-btn').disabled = true;
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') sendMessage();
        }
        
        function newSession() {
            localStorage.removeItem('orchestrator_sessionId');
            sessionId = null;
            document.getElementById('chat-container').innerHTML = '';
            if (ws) ws.close();
            connect();
        }
        
        connect();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_home():
    """Serve the chat UI."""
    return HTMLResponse(HTML_PAGE)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    session = None
    
    try:
        # Create or retrieve session
        if session_id:
            try:
                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )
                print(f"[WS] Retrieved session {session_id} for user {user_id}")
            except Exception as e:
                print(f"[WS] Session {session_id} not found, creating new: {e}")
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                )
        else:
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
            )
            print(f"[WS] Created new session {session.id} for user {user_id}")
        
        # Send session info
        await websocket.send_json({
            "type": "session",
            "session_id": session.id,
            "user_id": user_id,
        })
        
        # Load memory for this user
        try:
            memory_response = await memory_service.search_memory(
                app_name=APP_NAME,
                user_id=user_id,
                query="previous trip plans and preferences",
            )
            memory_list = getattr(memory_response, 'memories', []) or []
            if memory_list:
                await websocket.send_json({
                    "type": "memory_loaded",
                    "count": len(memory_list),
                })
                print(f"[Memory] Loaded {len(memory_list)} memories for user {user_id}")
        except Exception as e:
            print(f"[Memory] Search error: {e}")
        
        # Message loop
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "")
            
            if not user_text:
                continue
            
            print(f"[WS] User {user_id}: {user_text[:100]}...")
            
            try:
                # Run agent
                content = types.Content(
                    role="user",
                    parts=[types.Part(text=user_text)]
                )
                
                response_text = ""
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session.id,
                    new_message=content,
                ):
                    if hasattr(event, "content") and event.content:
                        if hasattr(event.content, "parts"):
                            for part in event.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_text += part.text
                
                await websocket.send_json({
                    "type": "response",
                    "text": response_text or "No response generated.",
                })
                
                # Update session reference
                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session.id,
                )
                
                # Store conversation content in state for memory extraction
                state = session.state or {}
                conversation_history = state.get("conversation_history", [])
                conversation_history.append({
                    "user": user_text,
                    "agent": response_text,
                })
                session.state["conversation_history"] = conversation_history[-10:]
                session.state["last_user_message"] = user_text
                session.state["last_agent_response"] = response_text
                
                # ALWAYS save to memory after every interaction
                try:
                    await memory_service.add_session_to_memory(session)
                    print(f"[Memory] Session {session.id} saved to Memory Bank")
                except Exception as e:
                    print(f"[Memory] Error saving: {e}")
                        
            except Exception as e:
                print(f"[WS] Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "text": str(e),
                })
                    
    except WebSocketDisconnect:
        print(f"[WS] User {user_id} disconnected")
        # Save session to memory on disconnect
        if session:
            try:
                await memory_service.add_session_to_memory(session)
                print(f"[Memory] Session saved on disconnect")
            except Exception as e:
                print(f"[Memory] Error saving on disconnect: {e}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_engine_id": ENGINE_ID,
        "app_name": APP_NAME,
    }


def main():
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Orchestrator Agent Web Interface on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

