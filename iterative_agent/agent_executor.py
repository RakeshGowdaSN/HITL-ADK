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
        """Safely extract task_id, context_id, and session_id from RequestContext."""
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
        
        # Try to extract session_id from context for session sharing
        session_id = (
            getattr(context, 'session_id', None) or
            getattr(getattr(context, 'task', None), 'session_id', None) or
            None
        )
        
        return task_id, context_id, session_id
    
    def _extract_session_from_message(self, message: str) -> str | None:
        """Extract session_id from message if passed in format [SESSION:xxx]."""
        import re
        match = re.search(r'\[SESSION:([^\]]+)\]', message)
        if match:
            return match.group(1)
        return None
    
    def _parse_revision_request(self, message: str) -> dict:
        """
        Parse REVISION_REQUEST from orchestrator to extract context.
        Handles both structured format and markdown format proposals.
        """
        import re
        result = {
            "feedback": "",
            "affected_section": "",
            "request": {},
            "route": "",
            "accommodation": "",
            "activities": "",
            "full_proposal": "",
        }
        
        # CRITICAL: Normalize escaped newlines to actual newlines
        message = message.replace('\\n', '\n')
        
        # Extract FEEDBACK
        feedback_match = re.search(r'FEEDBACK:\s*([^\n]+)', message)
        if feedback_match:
            result["feedback"] = feedback_match.group(1).strip()
        
        # Extract SECTION
        section_match = re.search(r'SECTION:\s*(\w+)', message)
        if section_match:
            result["affected_section"] = section_match.group(1).strip().lower()
        
        # Extract REQUEST info - try multiple patterns
        request_match = re.search(r'REQUEST:\s*destination=([^,]+),\s*start=([^,]+),\s*days=(\d+)', message)
        if request_match:
            result["request"] = {
                "destination": request_match.group(1).strip(),
                "start_location": request_match.group(2).strip(),
                "duration_days": int(request_match.group(3)),
            }
        else:
            # Try to extract from proposal text
            dest_match = re.search(r'trip.*?to\s+(\w+)', message, re.IGNORECASE)
            from_match = re.search(r'from\s+(\w+)', message, re.IGNORECASE)
            days_match = re.search(r'(\d+)[- ]day', message, re.IGNORECASE)
            if dest_match or from_match:
                result["request"] = {
                    "destination": dest_match.group(1) if dest_match else "destination",
                    "start_location": from_match.group(1) if from_match else "origin",
                    "duration_days": int(days_match.group(1)) if days_match else 2,
                }
        
        # Extract CURRENT_PROPOSAL
        proposal_match = re.search(r'CURRENT_PROPOSAL:\s*(.+?)(?:Route to iterative|$)', message, re.DOTALL)
        if proposal_match:
            proposal = proposal_match.group(1).strip()
            result["full_proposal"] = proposal
            
            # Try structured format first (ROUTE PLAN:, ACCOMMODATION:, ACTIVITIES:)
            route_patterns = [
                r'(ROUTE\s*PLAN:.*?)(?=ACCOMMODATION|ACTIVITIES|\*\*Hotels|\*\*Schedule|={10,}|-{10,}|$)',
                r'(\*\*Route\s*Description:?\*\*.*?)(?=\*\*Hotels|\*\*Accommodation|\*\*Schedule|\*\*Activities|$)',
                r'(Route:.*?)(?=Accommodation|Hotels|Activities|Schedule|$)',
            ]
            for pattern in route_patterns:
                match = re.search(pattern, proposal, re.DOTALL | re.IGNORECASE)
                if match and len(match.group(1).strip()) > 20:
                    result["route"] = match.group(1).strip()
                    break
            
            accom_patterns = [
                r'(ACCOMMODATION:.*?)(?=ROUTE|ACTIVITIES|\*\*Schedule|={10,}|-{10,}|$)',
                r'(\*\*Hotels:?\*\*.*?)(?=\*\*Route|\*\*Schedule|\*\*Activities|$)',
                r'(Hotels:.*?)(?=Route|Activities|Schedule|$)',
                r'(Accommodation:.*?)(?=Route|Activities|Schedule|$)',
            ]
            for pattern in accom_patterns:
                match = re.search(pattern, proposal, re.DOTALL | re.IGNORECASE)
                if match and len(match.group(1).strip()) > 20:
                    result["accommodation"] = match.group(1).strip()
                    break
            
            activities_patterns = [
                r'(ACTIVITIES\s*(&\s*ITINERARY)?:.*?)(?=ROUTE|ACCOMMODATION|SUMMARY|={10,}|-{10,}|$)',
                r'(\*\*Schedule:?\*\*.*?)(?=\*\*Route|\*\*Hotels|\*\*Accommodation|$)',
                r'(\*\*Activities:?\*\*.*?)(?=\*\*Route|\*\*Hotels|$)',
                r'(Schedule:.*?)(?=Route|Hotels|Accommodation|$)',
            ]
            for pattern in activities_patterns:
                match = re.search(pattern, proposal, re.DOTALL | re.IGNORECASE)
                if match and len(match.group(1).strip()) > 20:
                    result["activities"] = match.group(1).strip()
                    break
        
        print(f"[Parser] Feedback: {result['feedback']}, Section: {result['affected_section']}")
        print(f"[Parser] Request: {result['request']}")
        print(f"[Parser] Route len: {len(result['route'])}, Accom len: {len(result['accommodation'])}, Activities len: {len(result['activities'])}")
        print(f"[Parser] Full proposal len: {len(result['full_proposal'])}")
        
        return result

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
        task_id, context_id, shared_session_id = self._get_task_info(context)
        user_id = context_id
        
        # Also check if session_id is embedded in the message
        if not shared_session_id:
            shared_session_id = self._extract_session_from_message(query)
            if shared_session_id:
                # Remove the session marker from query
                query = query.replace(f'[SESSION:{shared_session_id}]', '').strip()
        
        updater = TaskUpdater(event_queue, task_id, context_id)
        
        # update_status expects a Message object, not a string
        await updater.update_status(
            TaskState.working, 
            new_agent_text_message(self.status_message, context_id, task_id)
        )

        try:
            # Try to reuse existing session if session_id was passed
            session = None
            if shared_session_id:
                try:
                    session = await self.session_service.get_session(
                        app_name=self.app_name,
                        user_id=user_id,
                        session_id=shared_session_id,
                    )
                    print(f"[Iterative Agent] Reusing shared session {session.id} for user {user_id}")
                except Exception as e:
                    print(f"[Iterative Agent] Could not get shared session: {e}")
            
            # Create new session if no shared session available
            if not session:
                session = await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                )
                print(f"[Iterative Agent] Created new session {session.id} for user {user_id}")
            
            # Parse REVISION_REQUEST and pre-populate state
            if "REVISION_REQUEST:" in query or "FEEDBACK:" in query:
                parsed = self._parse_revision_request(query)
                session.state["feedback"] = parsed["feedback"]
                session.state["affected_section"] = parsed["affected_section"]
                session.state["request"] = parsed["request"]
                
                # Store original sections so fix tools and present_revised_proposal can use them
                if parsed["route"]:
                    session.state["route"] = parsed["route"]
                if parsed["accommodation"]:
                    session.state["accommodation"] = parsed["accommodation"]
                if parsed["activities"]:
                    session.state["activities"] = parsed["activities"]
                
                # Store full proposal as fallback
                if parsed["full_proposal"]:
                    session.state["full_proposal"] = parsed["full_proposal"]
                    
                    # If individual sections weren't parsed, use full proposal with markers
                    if not parsed["route"]:
                        session.state["route"] = "[See full proposal for route details]"
                    if not parsed["activities"]:
                        session.state["activities"] = "[See full proposal for activities]"
                
                print(f"[Iterative Agent] Parsed: section={parsed['affected_section']}, feedback={parsed['feedback']}")
                print(f"[Iterative Agent] Sections found - Route: {bool(parsed['route'])}, Accom: {bool(parsed['accommodation'])}, Activities: {bool(parsed['activities'])}")
            
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
            
            # Store conversation content in state for memory extraction
            state = session.state or {}
            conversation_history = state.get("conversation_history", [])
            conversation_history.append({
                "user_feedback": query,
                "agent_response": response_text,
                "agent": "iterative_agent",
            })
            session.state["conversation_history"] = conversation_history[-10:]
            session.state["last_revision"] = response_text
            
            # ALWAYS save to Memory Bank after every execution
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

