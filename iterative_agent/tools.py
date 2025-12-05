"""Tools for Iterative Agent - fixing and revising proposals."""

from google.adk.tools import ToolContext


def fix_route(
    improved_route: str,
    transportation: str,
    estimated_time: str,
    tool_context: ToolContext,
) -> str:
    """Fix route based on user feedback."""
    feedback = tool_context.state.get("feedback", "user feedback")
    
    route = f"""ROUTE PLAN (REVISED based on: {feedback}):
{improved_route}

Transportation: {transportation}
Estimated Travel Time: {estimated_time}"""
    
    tool_context.state["route"] = route
    return f"Route updated based on feedback: {feedback}"


def fix_accommodation(
    improved_hotels: str,
    price_range: str,
    locations: str,
    tool_context: ToolContext,
) -> str:
    """Fix accommodation based on user feedback."""
    feedback = tool_context.state.get("feedback", "user feedback")
    
    accommodation = f"""ACCOMMODATION (REVISED based on: {feedback}):
{improved_hotels}

Price Range: {price_range}
Locations: {locations}"""
    
    tool_context.state["accommodation"] = accommodation
    return f"Accommodation updated based on feedback: {feedback}"


def fix_activities(
    improved_activities: str,
    highlights: str,
    schedule: str,
    tool_context: ToolContext,
) -> str:
    """Fix activities based on user feedback."""
    feedback = tool_context.state.get("feedback", "user feedback")
    
    activities = f"""ACTIVITIES & ITINERARY (REVISED based on: {feedback}):
{improved_activities}

Highlights: {highlights}

Schedule:
{schedule}"""
    
    tool_context.state["activities"] = activities
    return f"Activities updated based on feedback: {feedback}"


def present_revised_proposal(
    summary: str,
    tool_context: ToolContext,
) -> str:
    """
    Present the revised proposal for re-approval.
    State is pre-populated by agent_executor with original sections from CURRENT_PROPOSAL.
    
    Args:
        summary: Summary of changes made
    """
    request = tool_context.state.get("request", {})
    feedback = tool_context.state.get("feedback", "your feedback")
    full_proposal = tool_context.state.get("full_proposal", "")
    
    # State is pre-populated with original sections, fix tools update only their section
    route = tool_context.state.get("route", "")
    accommodation = tool_context.state.get("accommodation", "")
    activities = tool_context.state.get("activities", "")
    
    destination = request.get('destination', 'your destination')
    start_location = request.get('start_location', 'your location')
    duration = request.get('duration_days', 'N/A')
    
    # If sections look like placeholders, try to use full_proposal
    if route.startswith("[See full") or not route:
        route = "Route details from original proposal"
    if activities.startswith("[See full") or not activities:
        activities = "Activities from original proposal"
    
    # Build proposal - include full_proposal reference if sections weren't parsed properly
    if full_proposal and (not route or route == "Route details from original proposal"):
        # Couldn't parse sections - show what we updated plus reference to original
        proposal = f"""
================================================================================
REVISED TRIP PROPOSAL (Updated based on: {feedback})
{start_location} to {destination}
Duration: {duration} days
================================================================================

**UPDATED SECTION - {tool_context.state.get('affected_section', 'accommodation').upper()}:**

{accommodation}

--------------------------------------------------------------------------------

**OTHER SECTIONS (unchanged from original proposal):**

The route and activities remain the same as in the original proposal.

================================================================================
REVISION SUMMARY: {summary}
================================================================================

Please review this revised proposal and reply with:
- 'approve' to finalize this trip plan
- 'reject: <your feedback>' to request more changes
"""
    else:
        # Full sections available
        proposal = f"""
================================================================================
REVISED TRIP PROPOSAL (Updated based on: {feedback})
{start_location} to {destination}
Duration: {duration} days
================================================================================

{route}

--------------------------------------------------------------------------------

{accommodation}

--------------------------------------------------------------------------------

{activities}

================================================================================
REVISION SUMMARY: {summary}
================================================================================

Please review this revised proposal and reply with:
- 'approve' to finalize this trip plan
- 'reject: <your feedback>' to request more changes
"""
    
    tool_context.state["pending_proposal"] = proposal
    tool_context.state["awaiting_approval"] = True
    tool_context.state["last_revision"] = proposal
    
    return proposal

