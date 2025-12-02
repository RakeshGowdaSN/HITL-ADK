# HITL-ADK with Remote A2A Architecture

This project implements a Human-in-the-Loop (HITL) workflow using Google ADK with Remote Agent-to-Agent (A2A) protocol and VertexAI Memory Bank.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REMOTE A2A ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    VertexAI Memory Bank                              │   │
│   │                    (Shared across all agents)                        │   │
│   │                    user_id: "user123"                                │   │
│   │                    - "prefers budget hotels"                         │   │
│   │                    - "likes hiking activities"                       │   │
│   │                    - "previous trip to Paris"                        │   │
│   └───────────────────────────▲─────────────────────────────────────────┘   │
│                               │                                              │
│           ┌───────────────────┼───────────────────────────┐                 │
│           │                   │                           │                 │
│   ┌───────▼───────┐   ┌───────▼───────┐   ┌───────────────▼───────┐        │
│   │  Orchestrator │   │   Proposal    │   │     Iterative         │        │
│   │    Agent      │   │    Agent      │   │      Agent            │        │
│   │  (A2A Client) │   │  (A2A Server) │   │   (A2A Server)        │        │
│   │               │   │               │   │                       │        │
│   │  Agent Engine │   │   Cloud Run   │   │    Cloud Run          │        │
│   │               │   │               │   │                       │        │
│   │ load_memory() │   │ load_memory() │   │  load_memory()        │        │
│   │ save_memory() │   │ save_memory() │   │  save_memory()        │        │
│   └───────┬───────┘   └───────────────┘   └───────────────────────┘        │
│           │                   ▲                       ▲                     │
│           │     A2A Protocol  │                       │                     │
│           └───────────────────┴───────────────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Folder Structure

```
hitl-adk/
├── orchestrator_agent/          # A2A Client (deploys to Agent Engine)
│   ├── __init__.py
│   ├── agent.py                 # Root agent with RemoteA2aAgent sub-agents
│   ├── prompts.py
│   ├── tools.py                 # Orchestrator-specific tools
│   ├── run_orchestrator.py      # Local runner with Memory Bank
│   ├── requirements.txt
│   └── env_example.txt
│
├── proposal_agent/              # A2A Server (deploys to Cloud Run)
│   ├── __init__.py
│   ├── agent.py                 # SequentialAgent for trip generation
│   ├── agent_executor.py        # A2A executor with Memory Bank
│   ├── __main__.py              # A2A server entry point
│   ├── prompts.py
│   ├── tools.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── env_example.txt
│
├── iterative_agent/             # A2A Server (deploys to Cloud Run)
│   ├── __init__.py
│   ├── agent.py                 # LlmAgent for proposal fixes
│   ├── agent_executor.py        # A2A executor with Memory Bank
│   ├── __main__.py              # A2A server entry point
│   ├── prompts.py
│   ├── tools.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── env_example.txt
│
├── hitl_agent/                  # Original local implementation (for reference)
│   └── ...
│
├── setup_agent_engine.py        # Create Agent Engine for Memory Bank
└── A2A_README.md               # This file
```

## Memory Bank Integration

### How Memory Works Across Agents

1. **All agents use the same `AGENT_ENGINE_ID`** - This ensures they access the same Memory Bank
2. **User ID is consistent** - The `context_id` in A2A protocol carries the user identity
3. **Each agent has `load_memory` tool** - Can retrieve user preferences before generating
4. **Sessions are saved on approval** - `add_session_to_memory()` called when trip is finalized

### Memory Flow

```
User Session 1:
  Orchestrator → load_memory("preferences") → No memories found
  Proposal Agent → generates default trip
  User approves → save_memory() → Memory Bank stores:
    - "User planned trip to Kerala"
    - "User prefers budget hotels"
    - "User likes backwaters"

User Session 2 (next day):
  Orchestrator → load_memory("preferences") → Found: "prefers budget hotels"
  Proposal Agent → load_memory("hotel preferences") → Found: "prefers budget hotels"
  Agent automatically suggests budget-friendly options!
```

## Deployment Guide

### Step 1: Create Agent Engine

```bash
cd hitl-adk
python setup_agent_engine.py
```

Save the `AGENT_ENGINE_ID` - you'll need it for all agents.

### Step 2: Deploy Proposal Agent to Cloud Run

```bash
cd proposal_agent

# Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/proposal-agent

# Deploy to Cloud Run
gcloud run deploy proposal-agent-service \
  --image gcr.io/YOUR_PROJECT/proposal-agent \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_ID=your-engine-id,GOOGLE_CLOUD_PROJECT=your-project,MODEL_ID=gemini-2.5-pro"
```

### Step 3: Deploy Iterative Agent to Cloud Run

```bash
cd iterative_agent

# Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/iterative-agent

# Deploy to Cloud Run
gcloud run deploy iterative-agent-service \
  --image gcr.io/YOUR_PROJECT/iterative-agent \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_ID=your-engine-id,GOOGLE_CLOUD_PROJECT=your-project,MODEL_ID=gemini-2.5-pro"
```

### Step 4: Update Orchestrator URLs

Edit `orchestrator_agent/.env`:

```env
PROPOSAL_AGENT_URL=https://proposal-agent-service-XXXXX.us-east1.run.app/.well-known/agent.json
ITERATIVE_AGENT_URL=https://iterative-agent-service-XXXXX.us-east1.run.app/.well-known/agent.json
```

### Step 5: Run Orchestrator

```bash
cd orchestrator_agent
cp env_example.txt .env
# Edit .env with your values

python run_orchestrator.py
```

## Local Testing

### Test Proposal Agent Locally

```bash
cd proposal_agent
cp env_example.txt .env
# Edit .env

python -m __main__ --port 8080
```

### Test Iterative Agent Locally

```bash
cd iterative_agent
cp env_example.txt .env
# Edit .env

python -m __main__ --port 8081
```

### Test Orchestrator with Local Agents

Update `orchestrator_agent/.env`:

```env
PROPOSAL_AGENT_URL=http://localhost:8080/.well-known/agent.json
ITERATIVE_AGENT_URL=http://localhost:8081/.well-known/agent.json
```

Then run:

```bash
cd orchestrator_agent
python run_orchestrator.py
```

## HITL Workflow

1. **User requests trip**: "Plan a 5-day trip to Kerala from Bangalore"
2. **Orchestrator captures request** and delegates to `proposal_agent`
3. **Proposal Agent** (SequentialAgent):
   - `route_agent` → generates route, calls `load_memory` for preferences
   - `accommodation_agent` → generates hotels
   - `activity_agent` → generates activities
   - `finalizer_agent` → presents complete proposal
4. **User reviews and responds**:
   - "approve" → Orchestrator calls `process_approval()`, saves to Memory Bank
   - "reject: cheaper hotels" → Orchestrator calls `process_rejection()`, delegates to `iterative_agent`
5. **Iterative Agent** fixes the specified section and re-presents
6. **Loop until approved**

## Key Files Explained

### agent_executor.py (Proposal & Iterative)

This is the critical integration point for A2A + Memory Bank:

```python
class ADKAgentExecutor(AgentExecutor):
    def __init__(self, agent, ...):
        # Initialize VertexAI services
        self.session_service = VertexAiSessionService(agent_engine_id=ENGINE_ID)
        self.memory_service = VertexAiMemoryBankService(agent_engine_id=ENGINE_ID)
        
        # Create runner with services
        self.runner = Runner(
            agent=agent,
            session_service=self.session_service,
            memory_service=self.memory_service,
        )

    async def execute(self, context, event_queue):
        # Extract user_id from A2A context
        user_id = context.task.context_id
        
        # Create session
        session = await self.session_service.create_session(...)
        
        # Run agent
        async for event in self.runner.run_async(...):
            ...
        
        # CRITICAL: Save to memory on approval
        if session.state.get("approved"):
            await self.memory_service.add_session_to_memory(session)
```

### RemoteA2aAgent (Orchestrator)

The orchestrator uses `RemoteA2aAgent` to call the Cloud Run deployed agents:

```python
proposal_agent = RemoteA2aAgent(
    name="proposal_agent",
    description="Generates trip proposals",
    agent_card="https://proposal-agent-service.run.app/.well-known/agent.json",
    timeout=3600,
)
```

## Troubleshooting

### Memory Bank Not Working

1. Ensure all agents use the **same AGENT_ENGINE_ID**
2. Check that `add_session_to_memory()` is called in `agent_executor.py`
3. Verify agents have `load_memory` in their tools list
4. Check Cloud Run logs for memory-related errors

### A2A Connection Issues

1. Verify Cloud Run services are deployed and accessible
2. Check agent card URL is correct (includes `.well-known/agent.json`)
3. Ensure Cloud Run allows unauthenticated access (or configure auth)
4. Check timeout values if requests are timing out

### State Not Transferred

Remember: A2A protocol does NOT transfer session state between agents!

Each agent:
- Creates its own session
- Uses Memory Bank to share cross-session facts
- Gets user preferences via `load_memory()` tool

For runtime state (like current trip request), pass it in the message content.

## Environment Variables Summary

| Variable | Required | Used By |
|----------|----------|---------|
| `AGENT_ENGINE_ID` | Yes | All agents |
| `GOOGLE_CLOUD_PROJECT` | Yes | All agents |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | All agents |
| `MODEL_ID` | No | All agents (default: gemini-2.5-pro) |
| `PROPOSAL_AGENT_URL` | Yes | Orchestrator only |
| `ITERATIVE_AGENT_URL` | Yes | Orchestrator only |
| `SERVICE_URL` | No | Proposal/Iterative (auto-set on Cloud Run) |

*On Cloud Run, use attached service account instead.

