"""HITL Tools for approval/rejection flow within chat."""

from typing import Literal
from google.adk.tools import ToolContext


def request_human_approval(
    proposal_content: str,
    proposal_type: str,
    tool_context: ToolContext,
) -> dict:
    """
    Present a proposal to the human for approval or rejection.
    This tool stores the proposal in state and waits for human decision.
    
    Args:
        proposal_content: The content/output that needs human approval
        proposal_type: Type of proposal (e.g., "code_review", "document", "plan")
        tool_context: ADK tool context for state management
    
    Returns:
        dict with status and instructions for the human
    """
    # Store proposal in session state for tracking
    tool_context.state["pending_proposal"] = {
        "content": proposal_content,
        "type": proposal_type,
        "status": "pending_approval"
    }
    tool_context.state["awaiting_human_decision"] = True
    
    return {
        "status": "awaiting_approval",
        "message": f"📋 **Proposal Ready for Review**\n\n"
                   f"**Type:** {proposal_type}\n\n"
                   f"**Content:**\n{proposal_content}\n\n"
                   f"---\n"
                   f"Please respond with:\n"
                   f"- **'approve'** or **'yes'** to proceed to the next step\n"
                   f"- **'reject: <reason>'** to request modifications\n\n"
                   f"Example: `reject: Please add more error handling`"
    }


def process_human_decision(
    decision: Literal["approve", "reject"],
    rejection_reason: str | None,
    tool_context: ToolContext,
) -> dict:
    """
    Process the human's approval or rejection decision.
    
    Args:
        decision: Either "approve" or "reject"
        rejection_reason: If rejected, the reason provided by human
        tool_context: ADK tool context for state management
    
    Returns:
        dict with next action to take
    """
    pending = tool_context.state.get("pending_proposal", {})
    
    if not pending:
        return {
            "status": "error",
            "message": "No pending proposal found. Please submit a proposal first."
        }
    
    tool_context.state["awaiting_human_decision"] = False
    
    if decision == "approve":
        # Mark as approved and signal to proceed
        tool_context.state["pending_proposal"]["status"] = "approved"
        tool_context.state["approved_content"] = pending["content"]
        tool_context.state["proceed_to_next_agent"] = True
        
        return {
            "status": "approved",
            "message": "✅ Proposal approved! Proceeding to the next processing step.",
            "content": pending["content"],
            "next_action": "process"
        }
    else:
        # Mark as rejected with reason
        tool_context.state["pending_proposal"]["status"] = "rejected"
        tool_context.state["rejection_reason"] = rejection_reason
        tool_context.state["needs_rectification"] = True
        tool_context.state["original_content"] = pending["content"]
        
        return {
            "status": "rejected",
            "message": f"❌ Proposal rejected.\n**Reason:** {rejection_reason}\n\n"
                       f"Initiating rectification process...",
            "rejection_reason": rejection_reason,
            "original_content": pending["content"],
            "next_action": "rectify"
        }


def submit_rectified_output(
    rectified_content: str,
    changes_made: str,
    tool_context: ToolContext,
) -> dict:
    """
    Submit rectified content after rejection, ready for re-approval.
    
    Args:
        rectified_content: The corrected/modified content
        changes_made: Summary of changes made based on rejection reason
        tool_context: ADK tool context for state management
    
    Returns:
        dict prompting for re-approval
    """
    original = tool_context.state.get("original_content", "")
    reason = tool_context.state.get("rejection_reason", "")
    
    # Update state for new approval cycle
    tool_context.state["pending_proposal"] = {
        "content": rectified_content,
        "type": tool_context.state.get("pending_proposal", {}).get("type", "rectified"),
        "status": "pending_approval",
        "is_rectification": True,
        "original_content": original,
        "changes_made": changes_made
    }
    tool_context.state["awaiting_human_decision"] = True
    tool_context.state["needs_rectification"] = False
    
    return {
        "status": "awaiting_approval",
        "message": f"🔄 **Rectified Proposal Ready for Review**\n\n"
                   f"**Original Rejection Reason:** {reason}\n\n"
                   f"**Changes Made:** {changes_made}\n\n"
                   f"**Rectified Content:**\n{rectified_content}\n\n"
                   f"---\n"
                   f"Please respond with:\n"
                   f"- **'approve'** or **'yes'** to proceed\n"
                   f"- **'reject: <reason>'** for further modifications"
    }


def execute_approved_action(
    action_description: str,
    tool_context: ToolContext,
) -> dict:
    """
    Execute the final approved action/content.
    This is called by the processor agent after approval.
    
    Args:
        action_description: Description of what action was executed
        tool_context: ADK tool context for state management
    
    Returns:
        dict with execution result
    """
    approved_content = tool_context.state.get("approved_content", "")
    
    # Clear the approval flow state
    tool_context.state["pending_proposal"] = None
    tool_context.state["proceed_to_next_agent"] = False
    tool_context.state["approved_content"] = None
    
    # Store in history for memory
    history = tool_context.state.get("execution_history", [])
    history.append({
        "content": approved_content,
        "action": action_description,
        "status": "executed"
    })
    tool_context.state["execution_history"] = history
    
    return {
        "status": "executed",
        "message": f"🚀 **Action Executed Successfully**\n\n"
                   f"**Action:** {action_description}\n\n"
                   f"The approved content has been processed.",
        "executed_content": approved_content
    }

