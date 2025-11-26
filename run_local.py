"""Local testing script for HITL Agent with VertexAI services."""

import asyncio
import os
import uuid
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.genai import types

from hitl_agent.agent import root_agent
from hitl_agent.services import get_session_service, get_memory_service


# Load environment variables
load_dotenv()


async def run_hitl_agent():
    """Run the HITL agent in a local interactive loop."""
    
    # Setup services
    session_service = get_session_service()
    memory_service = get_memory_service()
    
    # Create runner
    runner = Runner(
        agent=root_agent,
        app_name="hitl_agent",
        session_service=session_service,
        memory_service=memory_service,
    )
    
    # Create a new session
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    session = await session_service.create_session(
        app_name="hitl_agent",
        user_id=user_id,
    )
    
    print("\n" + "="*60)
    print("🤖 HITL Agent - Human-in-the-Loop Workflow")
    print("="*60)
    print(f"Session ID: {session.id}")
    print(f"User ID: {user_id}")
    print("\nWorkflow:")
    print("  1. Make a request (e.g., 'Write a Python function to sort a list')")
    print("  2. Review the proposal")
    print("  3. Type 'approve' or 'reject: <reason>'")
    print("  4. If rejected, see the rectified version")
    print("  5. Repeat until satisfied")
    print("\nType 'quit' or 'exit' to end the session.")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("\n📝 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Ending session. Goodbye!")
                
                # Save session to memory before exiting
                try:
                    await memory_service.add_session_to_memory(session)
                    print("💾 Session saved to memory.")
                except Exception as e:
                    print(f"⚠️ Could not save to memory: {e}")
                
                break
            
            # Run the agent
            print("\n🤖 Agent: ", end="", flush=True)
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
            
            response_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                # Handle different event types
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text
                
                # Check for tool calls and their results
                if hasattr(event, "actions"):
                    for action in event.actions:
                        if hasattr(action, "tool_response"):
                            # Tool response contains the actual output
                            pass
            
            if response_text:
                print(response_text)
            
            # Update session reference
            session = await session_service.get_session(
                app_name="hitl_agent",
                user_id=user_id,
                session_id=session.id,
            )
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Ending session.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    asyncio.run(run_hitl_agent())


if __name__ == "__main__":
    main()

