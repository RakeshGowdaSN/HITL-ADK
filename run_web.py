"""Custom web interface for HITL Agent with VertexAI Memory Bank.

This replaces 'adk web' to properly use VertexAI Session and Memory services
for cross-session persistence.
"""

import os
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
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
        app_name="hitl_agent",
        session_service=session_service,
        memory_service=memory_service,
    )
    
    print("\n" + "="*60)
    print("HITL Agent Web Interface")
    print("="*60)
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
    <title>HITL Agent</title>
    <style>
        :root {
            --bg-dark: #0f0f0f;
            --bg-chat: #1a1a1a;
            --accent: #4ade80;
            --accent-dim: #166534;
            --text: #e5e5e5;
            --text-dim: #737373;
            --border: #262626;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            background: var(--bg-dark);
            color: var(--text);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 { font-size: 1rem; color: var(--accent); font-weight: 500; }
        #session-info { font-size: 0.75rem; color: var(--text-dim); }
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .message {
            max-width: 80%;
            padding: 1rem;
            border-radius: 0.5rem;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .user {
            align-self: flex-end;
            background: var(--accent-dim);
            border: 1px solid var(--accent);
        }
        .agent {
            align-self: flex-start;
            background: var(--bg-chat);
            border: 1px solid var(--border);
        }
        .system {
            align-self: center;
            background: transparent;
            border: 1px dashed var(--border);
            color: var(--text-dim);
            font-size: 0.85rem;
        }
        #input-container {
            padding: 1rem 2rem;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 1rem;
        }
        #message-input {
            flex: 1;
            padding: 0.75rem 1rem;
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            background: var(--bg-chat);
            color: var(--text);
            font-family: inherit;
            font-size: 0.9rem;
        }
        #message-input:focus {
            outline: none;
            border-color: var(--accent);
        }
        button {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 0.5rem;
            background: var(--accent);
            color: var(--bg-dark);
            font-family: inherit;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        #new-session { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
    </style>
</head>
<body>
    <header>
        <h1>HITL Agent - Human-in-the-Loop</h1>
        <div>
            <span id="session-info">Connecting...</span>
            <button id="new-session" onclick="newSession()">New Session</button>
        </div>
    </header>
    <div id="chat-container"></div>
    <div id="input-container">
        <input type="text" id="message-input" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
        <button id="send-btn" onclick="sendMessage()">Send</button>
    </div>
    
    <script>
        let ws;
        let sessionId = localStorage.getItem('sessionId');
        let userId = localStorage.getItem('userId') || 'user_' + Math.random().toString(36).substr(2, 8);
        localStorage.setItem('userId', userId);
        
        function connect() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/${userId}` + (sessionId ? `?session_id=${sessionId}` : '');
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                addMessage('Connected to HITL Agent', 'system');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'session') {
                    sessionId = data.session_id;
                    localStorage.setItem('sessionId', sessionId);
                    document.getElementById('session-info').textContent = `Session: ${sessionId.substr(0, 8)}... | User: ${userId}`;
                } else if (data.type === 'response') {
                    addMessage(data.text, 'agent');
                    document.getElementById('send-btn').disabled = false;
                } else if (data.type === 'memory_loaded') {
                    addMessage(`Memory loaded: ${data.count} items from previous sessions`, 'system');
                }
            };
            
            ws.onclose = () => {
                addMessage('Disconnected. Reconnecting...', 'system');
                setTimeout(connect, 2000);
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
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') sendMessage();
        }
        
        function newSession() {
            localStorage.removeItem('sessionId');
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


@app.get("/")
async def get_home():
    return HTMLResponse(HTML_PAGE)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
    await websocket.accept()
    
    try:
        # Create or retrieve session
        if session_id:
            try:
                session = await session_service.get_session(
                    app_name="hitl_agent",
                    user_id=user_id,
                    session_id=session_id,
                )
            except Exception:
                session = await session_service.create_session(
                    app_name="hitl_agent",
                    user_id=user_id,
                )
        else:
            session = await session_service.create_session(
                app_name="hitl_agent",
                user_id=user_id,
            )
        
        await websocket.send_json({
            "type": "session",
            "session_id": session.id,
            "user_id": user_id,
        })
        
        # Load memory for this user
        try:
            memories = await memory_service.search_memory(
                app_name="hitl_agent",
                user_id=user_id,
                query="previous trip plans and preferences",
            )
            if memories:
                await websocket.send_json({
                    "type": "memory_loaded",
                    "count": len(memories),
                })
        except Exception as e:
            print(f"Memory search error: {e}")
        
        # Message loop
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "")
            
            if not user_text:
                continue
            
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
                app_name="hitl_agent",
                user_id=user_id,
                session_id=session.id,
            )
            
            # Check if session should be saved to memory (on approval)
            if session.state and session.state.get("approved"):
                try:
                    await memory_service.add_session_to_memory(session)
                    print(f"Session {session.id} saved to memory bank")
                except Exception as e:
                    print(f"Error saving to memory: {e}")
                    
    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")
        # Save session to memory on disconnect
        try:
            if session:
                await memory_service.add_session_to_memory(session)
                print(f"Session saved to memory on disconnect")
        except Exception as e:
            print(f"Error saving on disconnect: {e}")


def main():
    port = int(os.getenv("PORT", 8080))
    print(f"Starting HITL Agent Web Interface on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

