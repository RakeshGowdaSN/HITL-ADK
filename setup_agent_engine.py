"""Script to create an Agent Engine for VertexAI Session and Memory services."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Create a new Agent Engine instance."""
    
    print("\n" + "="*60)
    print("🔧 Agent Engine Setup for HITL Agent")
    print("="*60 + "\n")
    
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment.")
        print("   Please set it in your .env file first.")
        sys.exit(1)
    
    # Check if already have an engine ID
    existing_id = os.getenv("AGENT_ENGINE_ID")
    if existing_id:
        print(f"⚠️ You already have an AGENT_ENGINE_ID configured: {existing_id}")
        response = input("   Create a new one anyway? (y/N): ").strip().lower()
        if response != "y":
            print("   Keeping existing Agent Engine ID.")
            sys.exit(0)
    
    try:
        import vertexai
        
        print("📡 Connecting to VertexAI...")
        
        # Initialize client with API key
        client = vertexai.Client(api_key=api_key)
        
        print("📦 Creating Agent Engine...")
        
        # Create agent engine
        agent_engine = client.agent_engines.create(
            config={
                "display_name": "HITL Agent Engine",
                "description": "Agent Engine for Human-in-the-Loop workflow with Session and Memory services",
            }
        )
        
        # Extract the ID
        engine_id = agent_engine.api_resource.name.split('/')[-1]
        
        print("\n" + "="*60)
        print("✅ Agent Engine Created Successfully!")
        print("="*60)
        print(f"\n   Agent Engine ID: {engine_id}")
        print(f"\n   Add this to your .env file:")
        print(f"   AGENT_ENGINE_ID={engine_id}")
        print("\n" + "="*60 + "\n")
        
    except ImportError:
        print("❌ Error: vertexai package not installed.")
        print("   Run: pip install google-adk[vertexai]")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating Agent Engine: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

