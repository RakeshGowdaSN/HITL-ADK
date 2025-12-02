"""Tools for Orchestrator Agent."""

from google.adk.tools import ToolContext


def show_final_plan(
    tool_context: ToolContext,
) -> str:
    """Show the finalized trip plan from current session."""
    final_plan = tool_context.state.get("final_proposal")
    if final_plan:
        return f"Here is your finalized trip plan:\n\n{final_plan}"
    
    pending = tool_context.state.get("pending_proposal")
    if pending:
        return f"You have a pending proposal (not yet approved):\n\n{pending}"
    
    return "No trip plan found in current session. Would you like to plan a new trip?"


def recall_trip_info(
    tool_context: ToolContext,
) -> str:
    """Recall trip information from current session state."""
    request = tool_context.state.get("request", {})
    route = tool_context.state.get("route", "")
    accommodation = tool_context.state.get("accommodation", "")
    activities = tool_context.state.get("activities", "")
    finalized = tool_context.state.get("trip_finalized", False)
    
    if not request:
        return "No trip information found. Would you like to plan a new trip?"
    
    info = f"Trip to {request.get('destination', 'unknown')} from {request.get('start_location', 'unknown')}\n"
    info += f"Duration: {request.get('duration_days', '?')} days\n"
    info += f"Preferences: {request.get('preferences', 'none')}\n"
    info += f"Status: {'Finalized' if finalized else 'In progress'}\n\n"
    
    if route:
        info += f"{route}\n\n"
    if accommodation:
        info += f"{accommodation}\n\n"
    if activities:
        info += f"{activities}\n"
    
    return info


def capture_request(
    destination: str,
    start_location: str,
    duration_days: int,
    preferences: str,
    tool_context: ToolContext,
) -> str:
    """Capture user's travel request and store in state."""
    tool_context.state["request"] = {
        "destination": destination,
        "start_location": start_location,
        "duration_days": duration_days,
        "preferences": preferences,
    }
    tool_context.state["awaiting_approval"] = False
    return f"Request captured for {destination}. Delegating to proposal_agent."


def process_approval(
    tool_context: ToolContext,
) -> str:
    """Process approval and finalize the trip."""
    proposal = tool_context.state.get("pending_proposal", "")
    tool_context.state["final_proposal"] = proposal
    tool_context.state["awaiting_approval"] = False
    tool_context.state["trip_finalized"] = True
    tool_context.state["approved"] = True  # Triggers memory save
    
    return "Trip plan approved and finalized! Have a great trip!"


def process_rejection(
    feedback: str,
    affected_section: str,
    tool_context: ToolContext,
) -> str:
    """
    Process rejection with feedback.
    
    Args:
        feedback: What the user wants changed
        affected_section: Which section to fix (route/accommodation/activities)
    """
    tool_context.state["feedback"] = feedback
    tool_context.state["affected_section"] = affected_section
    tool_context.state["awaiting_approval"] = False
    
    return f"Feedback received: '{feedback}' for {affected_section}. Routing to iterative_agent."

