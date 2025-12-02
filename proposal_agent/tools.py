"""Tools for Proposal Agent."""

from google.adk.tools import ToolContext


def generate_route(
    route_description: str,
    transportation: str,
    estimated_time: str,
    tool_context: ToolContext,
) -> str:
    """Generate route plan and save to state."""
    route = f"""ROUTE PLAN:
{route_description}

Transportation: {transportation}
Estimated Travel Time: {estimated_time}"""
    
    tool_context.state["route"] = route
    return "Route plan saved to state."


def generate_accommodation(
    hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """Generate accommodation plan and save to state."""
    accommodation = f"""ACCOMMODATION:
{hotels}

Price Range: {price_range}
Locations: {locations}"""
    
    tool_context.state["accommodation"] = accommodation
    return "Accommodation plan saved to state."


def generate_activities(
    activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """Generate activity plan and save to state."""
    activities_plan = f"""ACTIVITIES & ITINERARY:
{activities}

Highlights: {highlights}

Schedule:
{schedule}"""
    
    tool_context.state["activities"] = activities_plan
    return "Activities plan saved to state."


def present_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """
    Combine all parts and present for human review.
    Sets awaiting_approval=True so next user message is treated as decision.
    """
    request = tool_context.state.get("request", {})
    route = tool_context.state.get("route", "No route generated")
    accommodation = tool_context.state.get("accommodation", "No accommodation generated")
    activities = tool_context.state.get("activities", "No activities generated")
    
    # Get destination from request or from the message context
    destination = request.get('destination', 'your destination')
    start_location = request.get('start_location', 'your location')
    duration = request.get('duration_days', 'N/A')
    preferences = request.get('preferences', 'none specified')
    
    proposal = f"""
================================================================================
TRIP PROPOSAL: {start_location} to {destination}
Duration: {duration} days | Preferences: {preferences}
================================================================================

{route}

--------------------------------------------------------------------------------

{accommodation}

--------------------------------------------------------------------------------

{activities}

================================================================================
SUMMARY: {summary}
================================================================================

Please review this proposal and reply with:
- 'approve' to finalize this trip plan
- 'reject: <your feedback>' to request changes (e.g., 'reject: need cheaper hotels')
"""
    
    tool_context.state["pending_proposal"] = proposal
    tool_context.state["awaiting_approval"] = True
    
    return proposal

