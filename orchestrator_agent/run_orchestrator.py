"""Run the Orchestrator Agent with VertexAI Memory Bank."""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.genai import types

from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import VertexAiSessionService

# Use factory function instead of importing root_agent directly
from agent import create_root_agent


def get_services():
    """Initialize VertexAI services."""
    engine_id = os.getenv("AGENT_ENGINE_ID")
    
    if not engine_id:
        raise ValueError("AGENT_ENGINE_ID is required. Run setup_agent_engine.py first.")
    
    session_service = VertexAiSessionService(agent_engine_id=engine_id)
    memory_service = VertexAiMemoryBankService(agent_engine_id=engine_id)
    
    return session_service, memory_service


async def main():
    """Run interactive chat with the orchestrator."""
    session_service, memory_service = get_services()
    
    # Create fresh agent instance inside async context
    # This prevents 'client has been closed' errors
    root_agent = create_root_agent()
    
    runner = Runner(
        agent=root_agent,
        app_name="hitl_orchestrator",
        session_service=session_service,
        memory_service=memory_service,
    )
    
    print("\n" + "="*60)
    print("HITL Orchestrator Agent")
    print("="*60)
    print("This agent coordinates with remote Proposal and Iterative agents.")
    print("Memory Bank is enabled for cross-session persistence.")
    print("\nCommands:")
    print("  - Type your message to chat")
    print("  - Type 'quit' or 'exit' to end")
    print("  - Type 'new' to start a new session")
    print("="*60 + "\n")
    
    user_id = input("Enter your user ID (or press Enter for 'default_user'): ").strip()
    if not user_id:
        user_id = "default_user"
    
    # Create initial session
    session = await session_service.create_session(
        app_name="hitl_orchestrator",
        user_id=user_id,
    )
    print(f"\nSession created: {session.id}")
    print(f"User ID: {user_id}\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                # Save session to memory before exiting
                try:
                    session = await session_service.get_session(
                        app_name="hitl_orchestrator",
                        user_id=user_id,
                        session_id=session.id,
                    )
                    if session.state:
                        await memory_service.add_session_to_memory(session)
                        print("\nSession saved to Memory Bank.")
                except Exception as e:
                    print(f"\nWarning: Could not save to memory: {e}")
                print("Goodbye!")
                break
            
            if user_input.lower() == 'new':
                # Start new session
                session = await session_service.create_session(
                    app_name="hitl_orchestrator",
                    user_id=user_id,
                )
                print(f"\nNew session created: {session.id}\n")
                continue
            
            # Send message to agent
            content = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
            
            print("\nAgent: ", end="", flush=True)
            
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                print(part.text, end="", flush=True)
            
            print("\n")
            
            # Check if approved and save to memory
            session = await session_service.get_session(
                app_name="hitl_orchestrator",
                user_id=user_id,
                session_id=session.id,
            )
            if session.state and session.state.get("approved"):
                try:
                    await memory_service.add_session_to_memory(session)
                    print("[Session saved to Memory Bank]\n")
                except Exception as e:
                    print(f"[Warning: Could not save to memory: {e}]\n")
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
