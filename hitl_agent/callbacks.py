"""Callbacks for HITL flow - parse user approval/rejection responses."""

import re
from typing import Any
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


def parse_approval_response(user_message: str) -> tuple[str | None, str | None]:
    """
    Parse user message to detect approval or rejection.
    
    Returns:
        Tuple of (decision, rejection_reason) where decision is "approve", "reject", or None
    """
    message_lower = user_message.lower().strip()
    
    # Check for approval patterns
    approval_patterns = [
        r"^approve[d]?$",
        r"^yes$",
        r"^ok$",
        r"^okay$",
        r"^lgtm$",
        r"^looks good$",
        r"^go ahead$",
        r"^proceed$",
        r"^accept[ed]?$",
        r"^confirm[ed]?$",
    ]
    
    for pattern in approval_patterns:
        if re.match(pattern, message_lower):
            return ("approve", None)
    
    # Check for rejection patterns with reason
    rejection_patterns = [
        r"^reject[ed]?:\s*(.+)$",
        r"^no[,:]?\s*(.+)$",
        r"^deny[,:]?\s*(.+)$",
        r"^revise[,:]?\s*(.+)$",
        r"^change[,:]?\s*(.+)$",
        r"^modify[,:]?\s*(.+)$",
        r"^fix[,:]?\s*(.+)$",
    ]
    
    for pattern in rejection_patterns:
        match = re.match(pattern, message_lower, re.IGNORECASE | re.DOTALL)
        if match:
            reason = match.group(1).strip() if match.groups() else "No specific reason provided"
            return ("reject", reason)
    
    # Simple rejection without clear reason
    simple_rejections = [r"^reject[ed]?$", r"^no$", r"^deny$"]
    for pattern in simple_rejections:
        if re.match(pattern, message_lower):
            return ("reject", "User rejected without specific reason")
    
    return (None, None)


def before_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """
    Before agent callback to intercept user messages and check for approval/rejection.
    This allows seamless HITL flow within the chat.
    """
    state = callback_context.state
    
    # Check if we're awaiting human decision
    if not state.get("awaiting_human_decision", False):
        return None
    
    # Get the latest user message from invocation context
    # The user's response is in the request
    user_request = callback_context.user_content
    if not user_request:
        return None
    
    # Extract text from user content
    user_text = ""
    if hasattr(user_request, "parts"):
        for part in user_request.parts:
            if hasattr(part, "text"):
                user_text += part.text
    elif isinstance(user_request, str):
        user_text = user_request
    
    if not user_text:
        return None
    
    # Parse the response
    decision, reason = parse_approval_response(user_text)
    
    if decision:
        # Store the parsed decision in state for the agent to use
        state["parsed_decision"] = decision
        state["parsed_reason"] = reason
        
        # Let the agent handle it with the parsed information
        # Return None to let normal processing continue with enriched state
        return None
    
    # If not a clear approval/rejection, ask for clarification
    if state.get("awaiting_human_decision"):
        # Return a prompt asking for clear decision
        return types.Content(
            role="model",
            parts=[types.Part(text=(
                "I'm waiting for your decision on the proposal. "
                "Please respond with:\n"
                "- **'approve'** to proceed\n"
                "- **'reject: <your reason>'** to request changes\n\n"
                "For example: `reject: Please add input validation`"
            ))]
        )
    
    return None

