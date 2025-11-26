"""HITL Tools using ADK's built-in confirmation mechanism."""

from google.adk.tools import ToolContext


async def submit_for_approval(
    combined_proposal: str,
    tool_context: ToolContext,
) -> dict:
    """
    Submit the combined proposal for human approval.
    Uses ADK's request_confirmation to pause and wait for human response.
    
    Args:
        combined_proposal: The full proposal combining all sub-agent outputs
        tool_context: ADK tool context
    
    Returns:
        dict with approval result
    """
    # Store proposal
    tool_context.state["pending_proposal"] = combined_proposal
    
    # Use ADK's built-in confirmation - this PAUSES and waits for human
    confirmation = await tool_context.request_confirmation(
        hint=f"Please review the complete proposal:\n\n{combined_proposal}\n\n---\nRespond 'approve' to accept, or describe what needs to change.",
        payload={"approved": False, "feedback": ""}
    )
    
    if confirmation and confirmation.payload.get("approved", False):
        tool_context.state["approved_content"] = combined_proposal
        return {
            "status": "approved",
            "message": "Proposal approved by human."
        }
    else:
        feedback = confirmation.payload.get("feedback", "No feedback") if confirmation else "Rejected"
        tool_context.state["rejection_feedback"] = feedback
        return {
            "status": "rejected",
            "feedback": feedback,
            "message": "Proposal rejected. Delegate to rectification_agent."
        }


async def finalize_approved(
    summary: str,
    tool_context: ToolContext,
) -> dict:
    """
    Finalize the approved proposal. Call this after human approval.
    
    Args:
        summary: Brief summary of what was approved
        tool_context: ADK tool context
    
    Returns:
        dict confirming completion
    """
    approved = tool_context.state.get("approved_content", "")
    
    # Track history
    history = tool_context.state.get("execution_history", [])
    history.append({
        "content": approved,
        "summary": summary,
        "status": "finalized"
    })
    tool_context.state["execution_history"] = history
    
    # Clear workflow state
    tool_context.state["pending_proposal"] = None
    tool_context.state["approved_content"] = None
    tool_context.state["route_plan"] = None
    tool_context.state["accommodation_plan"] = None
    tool_context.state["activity_plan"] = None
    
    return {
        "status": "finalized",
        "summary": summary,
        "message": f"Workflow complete: {summary}"
    }
