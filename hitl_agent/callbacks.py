"""Callbacks for HITL flow - currently minimal, can be extended."""

from google.adk.agents.callback_context import CallbackContext
from google.genai import types


def before_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """
    Before agent callback - can be used to intercept and modify requests.
    Currently passes through without modification.
    """
    # Just pass through - let the agent handle everything
    return None
