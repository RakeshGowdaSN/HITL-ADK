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
    Shows the updated section clearly and references the original proposal for unchanged parts.
    
    Args:
        summary: Summary of changes made
    """
    feedback = tool_context.state.get("feedback", "your feedback")
    affected_section = tool_context.state.get("affected_section", "accommodation")
    full_proposal = tool_context.state.get("full_proposal", "")
    
    # Get the UPDATED section (whichever was fixed)
    updated_content = ""
    if affected_section == "route":
        updated_content = tool_context.state.get("route", "Updated route options")
    elif affected_section == "accommodation":
        updated_content = tool_context.state.get("accommodation", "Updated accommodation options")
    elif affected_section == "activities":
        updated_content = tool_context.state.get("activities", "Updated activities")
    else:
        updated_content = tool_context.state.get("accommodation", "Updated options")
    
    # Simple, clear format showing what changed
    proposal = f"""
================================================================================
✅ PROPOSAL UPDATED
================================================================================

Based on your feedback: "{feedback}"

**WHAT CHANGED - {affected_section.upper()}:**

{updated_content}

--------------------------------------------------------------------------------

**UNCHANGED SECTIONS:**

All other parts of your trip plan (route, {'activities' if affected_section != 'activities' else 'accommodation'}, etc.) 
remain exactly as shown in the original proposal.

================================================================================
{summary}
================================================================================

Please reply:
- 'approve' to finalize this trip plan
- 'reject: <feedback>' to request more changes
"""
    
    tool_context.state["pending_proposal"] = proposal
    tool_context.state["awaiting_approval"] = True
    tool_context.state["last_revision"] = proposal
    
    return proposal
    
    tool_context.state["pending_proposal"] = proposal
    tool_context.state["awaiting_approval"] = True
    tool_context.state["last_revision"] = proposal
    
    return proposal

