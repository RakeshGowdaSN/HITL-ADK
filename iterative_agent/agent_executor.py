"""A2A Agent Executor for Iterative Agent with Memory Bank support."""

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
        
        # CRITICAL: Use the SAME app_name across ALL agents for shared memory!
        # This must match orchestrator and proposal_agent
        self.app_name = "hitl_trip_planner"
        
        # Create runner with services
        self.runner = Runner(
            app_name=self.app_name,
            agent=agent,
            session_service=self.session_service,
            memory_service=self.memory_service,
        )

    def _get_task_info(self, context: RequestContext):
        """Safely extract task_id and context_id from RequestContext."""
        # Try different attribute patterns based on A2A SDK version
        task_id = (
            getattr(context, 'task_id', None) or
            getattr(getattr(context, 'task', None), 'id', None) or
            getattr(context, 'id', None) or
            str(uuid.uuid4())
        )
        
        context_id = (
            getattr(context, 'context_id', None) or
            getattr(getattr(context, 'task', None), 'context_id', None) or
            getattr(context, 'session_id', None) or
            "default_user"
        )
        
        return task_id, context_id

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
        
        # Safely extract task info from context
        task_id, context_id = self._get_task_info(context)
        user_id = context_id
        
        updater = TaskUpdater(event_queue, task_id, context_id)
        
        # update_status expects a Message object, not a string
        await updater.update_status(
            TaskState.working, 
            new_agent_text_message(self.status_message, context_id, task_id)
        )

        try:
            # Create a new session for this execution
            session = await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
            )
            
            print(f"[Iterative Agent] Created session {session.id} for user {user_id}")
            
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
                app_name=self.app_name,
                user_id=user_id,
                session_id=session.id,
            )
            
            # Save to Memory Bank if trip was finalized/approved
            state = session.state or {}
            if state.get("trip_finalized") or state.get("approved"):
                try:
                    await self.memory_service.add_session_to_memory(session)
                    print(f"[Iterative Agent] Session {session.id} saved to Memory Bank")
                except Exception as mem_error:
                    print(f"[Iterative Agent] Warning: Could not save to memory: {mem_error}")

            # Add response as artifact
            await updater.add_artifact(
                [Part(root=TextPart(text=response_text))],
                name=self.artifact_name,
            )

            await updater.complete()

        except Exception as e:
            print(f"[Iterative Agent] Error: {e}")
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(
                    f'Error: {e!s}', 
                    context_id, 
                    task_id
                ),
                final=True,
            )

