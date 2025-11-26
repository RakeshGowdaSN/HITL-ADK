"""HITL Tools - each tool reads from and writes to state."""

from google.adk.tools import ToolContext


def capture_request(
    destination: str,
    start_location: str,
    duration_days: int,
    preferences: str,
    tool_context: ToolContext,
) -> str:
    """
    Capture the user's travel request and store in state.
    Called by root agent before delegating to proposal_agent.
    
    Args:
        destination: Where the user wants to go
        start_location: Where they're starting from
        duration_days: How many days for the trip
        preferences: Any preferences (budget, scenic, etc.)
        tool_context: ADK tool context
    """
    # Store request details in state for sub-agents to access
    tool_context.state["request"] = {
        "destination": destination,
        "start_location": start_location,
        "duration_days": duration_days,
        "preferences": preferences,
    }
    
    return f"Request captured: {duration_days}-day trip from {start_location} to {destination}. Preferences: {preferences}. Delegating to proposal_agent."


def generate_route(
    route_description: str,
    transportation: str,
    estimated_time: str,
    tool_context: ToolContext,
) -> str:
    """
    Generate and store the route plan.
    
    Args:
        route_description: The route details
        transportation: Transportation options
        estimated_time: Estimated travel time
        tool_context: ADK tool context
    """
    route = f"""
ROUTE:
{route_description}

Transportation: {transportation}
Estimated Time: {estimated_time}
"""
    tool_context.state["route"] = route
    return f"Route plan generated and saved."


def generate_accommodation(
    hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """
    Generate and store accommodation recommendations.
    
    Args:
        hotels: Hotel recommendations
        price_range: Budget/mid/luxury options
        locations: Where hotels are located
        tool_context: ADK tool context
    """
    accommodation = f"""
ACCOMMODATIONS:
{hotels}

Price Range: {price_range}
Locations: {locations}
"""
    tool_context.state["accommodation"] = accommodation
    return f"Accommodation plan generated and saved."


def generate_activities(
    activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """
    Generate and store activity suggestions.
    
    Args:
        activities: List of activities
        highlights: Must-see highlights
        schedule: Suggested schedule
        tool_context: ADK tool context
    """
    activities_plan = f"""
ACTIVITIES:
{activities}

Highlights: {highlights}
Schedule: {schedule}
"""
    tool_context.state["activities"] = activities_plan
    return f"Activity plan generated and saved."


def finalize_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """
    Combine all parts and finalize the proposal.
    This tool has require_confirmation=True - ADK will pause for human approval.
    
    Args:
        summary: Brief summary of the proposal
        tool_context: ADK tool context
    """
    request = tool_context.state.get("request", {})
    route = tool_context.state.get("route", "No route generated")
    accommodation = tool_context.state.get("accommodation", "No accommodation generated")
    activities = tool_context.state.get("activities", "No activities generated")
    
    full_proposal = f"""
========================================
TRIP PROPOSAL: {request.get('start_location', 'Start')} to {request.get('destination', 'Destination')}
Duration: {request.get('duration_days', 'N/A')} days
Preferences: {request.get('preferences', 'None')}
========================================

{route}

{accommodation}

{activities}

========================================
Summary: {summary}
========================================
"""
    
    tool_context.state["final_proposal"] = full_proposal
    
    return f"Proposal finalized:\n{full_proposal}"
