"""A2A Agent Executor for Proposal Agent with Memory Bank support."""

import os
import uuid

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task

from google.adk.runners import Runner
from google.genai import types
from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import VertexAiSessionService

from agent import root_agent


# Get Agent Engine ID from environment
ENGINE_ID = os.getenv("AGENT_ENGINE_ID")

if not ENGINE_ID:
    raise ValueError("AGENT_ENGINE_ID environment variable is required")


class ADKAgentExecutor(AgentExecutor):
    """A2A Executor that integrates ADK agents with VertexAI Memory Bank."""
    
    def __init__(
        self,
        agent,
        status_message='Processing request...',
        artifact_name='response',
    ):
        """Initialize the executor with VertexAI services."""
        self.agent = agent
        self.status_message = status_message
        self.artifact_name = artifact_name
        
        # Initialize VertexAI services for persistence
        self.session_service = VertexAiSessionService(agent_engine_id=ENGINE_ID)
        self.memory_service = VertexAiMemoryBankService(agent_engine_id=ENGINE_ID)
        
        # Create runner with services
        self.runner = Runner(
            app_name=agent.name,
            agent=agent,
            session_service=self.session_service,
            memory_service=self.memory_service,
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel execution (not implemented)."""
        raise NotImplementedError(
            'Cancellation is not implemented for ADKAgentExecutor.'
        )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent and handle Memory Bank operations."""
        if not context.message:
            raise ValueError('Message should be present in request context')

        query = context.get_user_input()
        
        # Extract user_id from A2A context
        # context_id is typically the user identifier in A2A protocol
        user_id = context.task.context_id or "default_user"
        
        updater = TaskUpdater(event_queue, context.task.id, context.task.context_id)
        
        await updater.update_status(TaskState.working, self.status_message)

        try:
            # Create a new session for this execution
            session = await self.session_service.create_session(
                app_name=self.agent.name,
                user_id=user_id,
            )
            
            print(f"[Proposal Agent] Created session {session.id} for user {user_id}")
            
            # Build the content message
            content = types.Content(
                role='user', 
                parts=[types.Part.from_text(text=query)]
            )

            response_text = ''
            
            # Run the agent
            async for event in self.runner.run_async(
                user_id=user_id, 
                session_id=session.id, 
                new_message=content
            ):
                if (
                    event.is_final_response()
                    and event.content
                    and event.content.parts
                ):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text + '\n'
                        elif hasattr(part, 'function_call'):
                            # Function calls are handled internally by ADK
                            pass

            # Get updated session with state after execution
            session = await self.session_service.get_session(
                app_name=self.agent.name,
                user_id=user_id,
                session_id=session.id,
            )
            
            # Save to Memory Bank if trip was finalized/approved
            state = session.state or {}
            if state.get("trip_finalized") or state.get("approved"):
                try:
                    await self.memory_service.add_session_to_memory(session)
                    print(f"[Proposal Agent] Session {session.id} saved to Memory Bank")
                except Exception as mem_error:
                    print(f"[Proposal Agent] Warning: Could not save to memory: {mem_error}")

            # Add response as artifact
            await updater.add_artifact(
                [Part(root=TextPart(text=response_text))],
                name=self.artifact_name,
            )

            await updater.complete()

        except Exception as e:
            print(f"[Proposal Agent] Error: {e}")
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(
                    f'Error: {e!s}', 
                    context.task.context_id, 
                    context.task.id
                ),
                final=True,
            )

