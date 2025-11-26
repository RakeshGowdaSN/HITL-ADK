"""Script to create an Agent Engine for VertexAI Session and Memory services."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path so we can import hitl_agent before installing.
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hitl_agent.services import create_agent_engine

# Load environment variables
load_dotenv()


def main():
    """Create a new Agent Engine instance."""

    print("\n" + "=" * 60)
    print("Agent Engine Setup for HITL Agent")
    print("=" * 60 + "\n")

    existing_id = os.getenv("AGENT_ENGINE_ID")
    if existing_id:
        print(f"You already have an AGENT_ENGINE_ID configured: {existing_id}")
        response = input("   Create a new one anyway? (y/N): ").strip().lower()
        if response != "y":
            print("   Keeping existing Agent Engine ID.")
            sys.exit(0)

    try:
        engine_id = create_agent_engine()
        print("\n" + "=" * 60)
        print("Agent Engine Created Successfully.")
        print("=" * 60)
        print(f"\n   Agent Engine ID: {engine_id}")
        print(f"\n   Add this to your .env file:")
        print(f"   AGENT_ENGINE_ID={engine_id}")
        print("\n" + "=" * 60 + "\n")
    except ValueError as ve:
        print(f"{ve}")
        print("   Provide GOOGLE_API_KEY or configure GOOGLE_APPLICATION_CREDENTIALS + GOOGLE_CLOUD_PROJECT.")
        sys.exit(1)
    except ImportError:
        print("Error: vertexai package not installed.")
        print("   Run: pip install google-adk[vertexai]")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating Agent Engine: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

