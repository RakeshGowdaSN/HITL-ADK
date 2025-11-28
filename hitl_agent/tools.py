"""HITL Tools - turn-based approval flow."""

from google.adk.tools import ToolContext


# ============================================================================
# RECALL / SHOW PREVIOUS TRIPS
# ============================================================================

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


# ============================================================================
# INITIAL REQUEST CAPTURE
# ============================================================================

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
    return f"Request captured. Delegating to proposal_agent."


# ============================================================================
# PROPOSAL GENERATION TOOLS
# ============================================================================

def generate_route(
    route_description: str,
    transportation: str,
    estimated_time: str,
    tool_context: ToolContext,
) -> str:
    """Generate route plan and save to state."""
    route = f"ROUTE:\n{route_description}\nTransportation: {transportation}\nTime: {estimated_time}"
    tool_context.state["route"] = route
    return "Route saved."


def generate_accommodation(
    hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """Generate accommodation plan and save to state."""
    accommodation = f"ACCOMMODATIONS:\n{hotels}\nPrice: {price_range}\nLocations: {locations}"
    tool_context.state["accommodation"] = accommodation
    return "Accommodation saved."


def generate_activities(
    activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """Generate activity plan and save to state."""
    activities_plan = f"ACTIVITIES:\n{activities}\nHighlights: {highlights}\nSchedule: {schedule}"
    tool_context.state["activities"] = activities_plan
    return "Activities saved."


def present_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """
    Combine all parts and present for human review.
    Sets awaiting_approval=True so next user message is treated as decision.
    """
    request = tool_context.state.get("request", {})
    route = tool_context.state.get("route", "No route")
    accommodation = tool_context.state.get("accommodation", "No accommodation")
    activities = tool_context.state.get("activities", "No activities")
    
    proposal = f"""
================================================================================
TRIP PROPOSAL: {request.get('start_location')} → {request.get('destination')}
Duration: {request.get('duration_days')} days | Preferences: {request.get('preferences')}
================================================================================

{route}

{accommodation}

{activities}

================================================================================
Summary: {summary}
================================================================================

Please review and reply with:
- 'approve' to finalize this trip plan
- 'reject: <your feedback>' to request changes (e.g., 'reject: need cheaper hotels')
"""
    tool_context.state["pending_proposal"] = proposal
    tool_context.state["awaiting_approval"] = True
    
    return proposal


# ============================================================================
# APPROVAL HANDLING TOOLS
# ============================================================================

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
    
    return f"Feedback received: '{feedback}' for {affected_section}. Routing to fix."


# ============================================================================
# CORRECTION TOOLS
# ============================================================================

def fix_route(
    improved_route: str,
    transportation: str,
    estimated_time: str,
    tool_context: ToolContext,
) -> str:
    """Fix route based on feedback."""
    feedback = tool_context.state.get("feedback", "")
    route = f"ROUTE (REVISED - {feedback}):\n{improved_route}\nTransportation: {transportation}\nTime: {estimated_time}"
    tool_context.state["route"] = route
    return "Route updated."


def fix_accommodation(
    improved_hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """Fix accommodation based on feedback."""
    feedback = tool_context.state.get("feedback", "")
    accommodation = f"ACCOMMODATIONS (REVISED - {feedback}):\n{improved_hotels}\nPrice: {price_range}\nLocations: {locations}"
    tool_context.state["accommodation"] = accommodation
    return "Accommodation updated."


def fix_activities(
    improved_activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """Fix activities based on feedback."""
    feedback = tool_context.state.get("feedback", "")
    activities = f"ACTIVITIES (REVISED - {feedback}):\n{improved_activities}\nHighlights: {highlights}\nSchedule: {schedule}"
    tool_context.state["activities"] = activities
    return "Activities updated."


def present_revised_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """Present revised proposal for re-approval."""
    request = tool_context.state.get("request", {})
    route = tool_context.state.get("route", "No route")
    accommodation = tool_context.state.get("accommodation", "No accommodation")
    activities = tool_context.state.get("activities", "No activities")
    feedback = tool_context.state.get("feedback", "")
    
    proposal = f"""
================================================================================
REVISED TRIP PROPOSAL (based on your feedback: {feedback})
{request.get('start_location')} → {request.get('destination')}
Duration: {request.get('duration_days')} days | Preferences: {request.get('preferences')}
================================================================================

{route}

{accommodation}

{activities}

================================================================================
Summary: {summary}
================================================================================

Please review and reply with:
- 'approve' to finalize this trip plan
- 'reject: <your feedback>' to request more changes
"""
    tool_context.state["pending_proposal"] = proposal
    tool_context.state["awaiting_approval"] = True
    
    return proposal
