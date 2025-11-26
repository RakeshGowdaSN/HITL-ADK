"""HITL Tools - using FunctionTool with require_confirmation=True."""

from google.adk.tools import ToolContext


def execute_proposal(
    route_plan: str,
    accommodation_plan: str,
    activity_plan: str,
    tool_context: ToolContext,
) -> dict:
    """
    Execute the complete proposal after human confirms.
    This tool uses require_confirmation=True so ADK will pause for approval.
    
    Args:
        route_plan: The route planning section
        accommodation_plan: The accommodation section
        activity_plan: The activities section
        tool_context: ADK tool context
    
    Returns:
        dict with the finalized proposal
    """
    # Combine all parts
    combined = f"""
ROUTE PLAN:
{route_plan}

ACCOMMODATIONS:
{accommodation_plan}

ACTIVITIES:
{activity_plan}
"""
    
    # Store in state
    tool_context.state["approved_content"] = combined
    
    # Track history
    history = tool_context.state.get("execution_history", [])
    history.append({
        "content": combined,
        "status": "finalized"
    })
    tool_context.state["execution_history"] = history
    
    return {
        "status": "finalized",
        "message": "Proposal approved and finalized.",
        "content": combined
    }


def submit_rectified(
    rectified_content: str,
    what_was_fixed: str,
    tool_context: ToolContext,
) -> dict:
    """
    Submit rectified content after human confirms the fix.
    This tool uses require_confirmation=True so ADK will pause for approval.
    
    Args:
        rectified_content: The improved content
        what_was_fixed: Description of what was changed
        tool_context: ADK tool context
    
    Returns:
        dict with result
    """
    tool_context.state["approved_content"] = rectified_content
    
    return {
        "status": "finalized",
        "message": f"Rectified proposal approved. Fixed: {what_was_fixed}",
        "content": rectified_content
    }
