"""A2A Server entry point for Iterative Agent."""

import asyncio
import functools
import logging
import os

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from starlette.applications import Starlette

from dotenv import load_dotenv
load_dotenv()

from agent import root_agent
from agent_executor import ADKAgentExecutor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""
    pass


def make_sync(f):
    """Decorator to run async function synchronously."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@click.command()
@click.option('--host', default='0.0.0.0', help='Host to bind the server to.')
@click.option('--port', default=8081, help='Port to run the server on.')
@make_sync
async def main(host, port):
    """Start the Iterative Agent A2A server."""
    
    # Define agent skill
    skill = AgentSkill(
        id="ProposalRevision",
        name="Iterative_Agent",
        description="Revises and fixes specific parts of a trip proposal based on user feedback. Can fix route, accommodation, or activities while keeping other parts unchanged.",
        tags=[
            "travel-planning",
            "proposal-revision",
            "feedback-handling",
            "human-in-the-loop",
            "iterative-improvement"
        ],
        examples=[
            "The hotels are too expensive, suggest budget options under $100/night.",
            "I want more outdoor activities and hiking trails.",
            "Change the route to avoid flying, prefer trains.",
            "Need more restaurant recommendations in the itinerary."
        ]
    )
    
    # Get the service URL from environment or use default
    service_url = os.getenv(
        "SERVICE_URL", 
        f"http://{host}:{port}"
    )
    
    # Define agent card
    agent_card = AgentCard(
        name="ProposalRevision",
        description="An LlmAgent that fixes and revises specific parts of trip proposals based on user feedback, with Memory Bank integration for personalized corrections.",
        url=service_url,
        version="1.0.0",
        defaultInputModes=["text/plain"],
        defaultOutputModes=["application/json"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
        supportsAuthenticatedExtendedCard=True,
    )
    
    # Create task store
    task_store = InMemoryTaskStore()
    
    # Create request handler with our executor
    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(
            agent=root_agent,
            status_message="Revising proposal based on feedback...",
            artifact_name="revision_response",
        ),
        task_store=task_store,
    )
    
    # Create A2A application
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, 
        http_handler=request_handler
    )
    
    routes = a2a_app.routes()
    app = Starlette(
        routes=routes,
        middleware=[],
    )
    
    # Print startup info
    print("\n" + "="*60)
    print("ITERATIVE AGENT - A2A Server")
    print("="*60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Service URL: {service_url}")
    print(f"Agent Engine ID: {os.getenv('AGENT_ENGINE_ID', 'NOT SET')}")
    print("="*60)
    print("\nEndpoints:")
    print(f"  GET  {service_url}/.well-known/agent.json")
    print(f"  POST {service_url}/")
    print("="*60 + "\n")
    
    config = uvicorn.Config(app, host=host, port=port, log_level='info')
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == '__main__':
    main()

