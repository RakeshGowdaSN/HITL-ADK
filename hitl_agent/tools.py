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
    
    Args:
        decision: Either "approve" or "reject"
        rejection_reason: If rejected, the reason provided by human (can be None)
        tool_context: ADK tool context for state management
    
    Returns:
        dict indicating next action
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
            "message": "Proposal approved. Call finalize_approved_content to complete the workflow.",
            "content": pending["content"],
            "next_action": "finalize"
        }
    else:
        tool_context.state["pending_proposal"]["status"] = "rejected"
        tool_context.state["rejection_reason"] = rejection_reason or "No reason given"
        tool_context.state["original_content"] = pending["content"]
        
        return {
            "status": "rejected",
            "message": "Proposal rejected. Delegate to rectification_agent to fix the specific part.",
            "rejection_reason": rejection_reason or "No reason given",
            "original_content": pending["content"],
            "next_action": "delegate_to_rectification_agent"
        }


def submit_rectified_output(
    rectified_content: str,
    changes_made: str,
    sub_agent_used: str,
    tool_context: ToolContext,
) -> dict:
    """
    Submit improved content after rejection.
    
    Args:
        rectified_content: The improved content
        changes_made: Summary of what was changed
        sub_agent_used: Which sub-agent was used for rectification
        tool_context: ADK tool context for state management
    
    Returns:
        dict prompting for re-approval
    """
    reason = tool_context.state.get("rejection_reason", "")
    
    tool_context.state["pending_proposal"] = {
        "content": rectified_content,
        "type": tool_context.state.get("pending_proposal", {}).get("type", "rectified"),
        "status": "pending",
        "changes_made": changes_made,
        "sub_agent_used": sub_agent_used
    }
    tool_context.state["awaiting_decision"] = True
    
    return {
        "status": "awaiting_approval",
        "message": "Rectified content ready for review.",
        "original_feedback": reason,
        "changes_made": changes_made,
        "sub_agent_used": sub_agent_used,
        "content": rectified_content,
        "instructions": "Waiting for user to respond with 'approve' or 'reject: reason'"
    }


def finalize_approved_content(
    summary: str,
    tool_context: ToolContext,
) -> dict:
    """
    Finalize the approved content and end the workflow.
    Call this after human approves the proposal.
    
    Args:
        summary: Brief summary of what was approved
        tool_context: ADK tool context for state management
    
    Returns:
        dict confirming completion
    """
    approved_content = tool_context.state.get("approved_content", "")
    approved_type = tool_context.state.get("approved_type", "content")
    
    # Track in history
    history = tool_context.state.get("execution_history", [])
    history.append({
        "content": approved_content,
        "type": approved_type,
        "summary": summary,
        "status": "finalized"
    })
    tool_context.state["execution_history"] = history
    
    # Clear workflow state
    tool_context.state["pending_proposal"] = None
    tool_context.state["approved_content"] = None
    tool_context.state["approved_type"] = None
    tool_context.state["awaiting_decision"] = False
    
    return {
        "status": "finalized",
        "summary": summary,
        "message": f"Workflow complete. {summary}"
    }
