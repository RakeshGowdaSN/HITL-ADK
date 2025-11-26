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
    Call this AFTER generating content that needs human review.
    
    Args:
        proposal_content: The content/output that needs human approval
        proposal_type: Type of proposal (e.g., "code", "document", "plan")
        tool_context: ADK tool context for state management
    
    Returns:
        dict with status and instructions for the human
    """
    tool_context.state["pending_proposal"] = {
        "content": proposal_content,
        "type": proposal_type,
        "status": "pending"
    }
    tool_context.state["awaiting_decision"] = True
    
    return {
        "status": "awaiting_approval",
        "proposal_type": proposal_type,
        "content": proposal_content,
        "instructions": "Waiting for user to respond with 'approve' or 'reject: reason'"
    }


def process_human_decision(
    decision: Literal["approve", "reject"],
    rejection_reason: str | None,
    tool_context: ToolContext,
) -> dict:
    """
    Process the human's approval or rejection decision.
    Call this when user responds with approve/reject.
    
    Args:
        decision: Either "approve" or "reject"
        rejection_reason: If rejected, the reason provided by human (can be None)
        tool_context: ADK tool context for state management
    
    Returns:
        dict indicating next action - delegate to next_agent or rectification_agent
    """
    pending = tool_context.state.get("pending_proposal", {})
    
    if not pending:
        return {
            "status": "error",
            "message": "No pending proposal found."
        }
    
    tool_context.state["awaiting_decision"] = False
    
    if decision == "approve":
        tool_context.state["pending_proposal"]["status"] = "approved"
        tool_context.state["approved_content"] = pending["content"]
        tool_context.state["approved_type"] = pending["type"]
        
        return {
            "status": "approved",
            "message": "Proposal approved. Now delegate to next_agent to handle the approved content.",
            "content": pending["content"],
            "next_action": "delegate_to_next_agent"
        }
    else:
        tool_context.state["pending_proposal"]["status"] = "rejected"
        tool_context.state["rejection_reason"] = rejection_reason or "No reason given"
        tool_context.state["original_content"] = pending["content"]
        
        return {
            "status": "rejected",
            "message": "Proposal rejected. Now delegate to rectification_agent to improve the content.",
            "rejection_reason": rejection_reason or "No reason given",
            "original_content": pending["content"],
            "next_action": "delegate_to_rectification_agent"
        }


def submit_rectified_output(
    rectified_content: str,
    changes_made: str,
    tool_context: ToolContext,
) -> dict:
    """
    Submit improved content after rejection.
    Call this after improving content based on rejection feedback.
    
    Args:
        rectified_content: The improved content
        changes_made: Summary of what was changed
        tool_context: ADK tool context for state management
    
    Returns:
        dict prompting for re-approval
    """
    reason = tool_context.state.get("rejection_reason", "")
    
    tool_context.state["pending_proposal"] = {
        "content": rectified_content,
        "type": tool_context.state.get("pending_proposal", {}).get("type", "rectified"),
        "status": "pending",
        "changes_made": changes_made
    }
    tool_context.state["awaiting_decision"] = True
    
    return {
        "status": "awaiting_approval",
        "message": "Rectified content ready for review.",
        "original_feedback": reason,
        "changes_made": changes_made,
        "content": rectified_content,
        "instructions": "Waiting for user to respond with 'approve' or 'reject: reason'"
    }
