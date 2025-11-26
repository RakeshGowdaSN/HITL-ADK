"""HITL Tools - proposal generation, approval, and iterative correction."""

from google.adk.tools import ToolContext


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
    return f"Request captured: {duration_days}-day trip from {start_location} to {destination}. Delegating to proposal_agent."


# ============================================================================
# PROPOSAL GENERATION TOOLS (used by SequentialAgent sub-agents)
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
    return "Route plan saved."


def generate_accommodation(
    hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """Generate accommodation plan and save to state."""
    accommodation = f"ACCOMMODATIONS:\n{hotels}\nPrice: {price_range}\nLocations: {locations}"
    tool_context.state["accommodation"] = accommodation
    return "Accommodation plan saved."


def generate_activities(
    activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """Generate activity plan and save to state."""
    activities_plan = f"ACTIVITIES:\n{activities}\nHighlights: {highlights}\nSchedule: {schedule}"
    tool_context.state["activities"] = activities_plan
    return "Activity plan saved."


def finalize_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """
    Combine all parts and finalize. Has require_confirmation=True.
    ADK will pause for human approval before executing.
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
"""
    tool_context.state["final_proposal"] = proposal
    return f"Proposal ready for approval:\n{proposal}"


# ============================================================================
# ITERATIVE CORRECTION TOOLS (used by iterative_agent)
# ============================================================================

def store_feedback(
    feedback: str,
    affected_section: str,
    tool_context: ToolContext,
) -> str:
    """
    Store human feedback for correction.
    
    Args:
        feedback: What the human wants changed
        affected_section: Which section to fix (route/accommodation/activities)
    """
    tool_context.state["feedback"] = feedback
    tool_context.state["affected_section"] = affected_section
    return f"Feedback stored: '{feedback}' for section: {affected_section}"


def fix_route(
    improved_route: str,
    transportation: str,
    estimated_time: str,
    tool_context: ToolContext,
) -> str:
    """Fix route based on feedback."""
    feedback = tool_context.state.get("feedback", "")
    route = f"ROUTE (REVISED based on feedback: {feedback}):\n{improved_route}\nTransportation: {transportation}\nTime: {estimated_time}"
    tool_context.state["route"] = route
    return "Route updated based on feedback."


def fix_accommodation(
    improved_hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """Fix accommodation based on feedback."""
    feedback = tool_context.state.get("feedback", "")
    accommodation = f"ACCOMMODATIONS (REVISED based on feedback: {feedback}):\n{improved_hotels}\nPrice: {price_range}\nLocations: {locations}"
    tool_context.state["accommodation"] = accommodation
    return "Accommodation updated based on feedback."


def fix_activities(
    improved_activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """Fix activities based on feedback."""
    feedback = tool_context.state.get("feedback", "")
    activities = f"ACTIVITIES (REVISED based on feedback: {feedback}):\n{improved_activities}\nHighlights: {highlights}\nSchedule: {schedule}"
    tool_context.state["activities"] = activities
    return "Activities updated based on feedback."


def resubmit_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """
    Resubmit the corrected proposal for approval.
    Has require_confirmation=True - ADK will pause for human approval.
    """
    request = tool_context.state.get("request", {})
    route = tool_context.state.get("route", "No route")
    accommodation = tool_context.state.get("accommodation", "No accommodation")
    activities = tool_context.state.get("activities", "No activities")
    feedback = tool_context.state.get("feedback", "")
    
    proposal = f"""
================================================================================
REVISED TRIP PROPOSAL (after feedback: {feedback})
{request.get('start_location')} → {request.get('destination')}
Duration: {request.get('duration_days')} days | Preferences: {request.get('preferences')}
================================================================================

{route}

{accommodation}

{activities}

================================================================================
Summary: {summary}
================================================================================
"""
    tool_context.state["final_proposal"] = proposal
    return f"Revised proposal ready for approval:\n{proposal}"
