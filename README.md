# HITL Agent - Human-in-the-Loop with Google ADK

# A human-in-the-loop workflow built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/).

- **VertexAI Session Service** for persistent session management
- **VertexAI Memory Bank Service** to capture approvals and outcomes
- **Approval/rejection flow entirely in chat**
- **Multi-agent architecture**: proposal, rectification, and processor agents

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Root Agent (Orchestrator)                 │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Proposal   │───▶│    Human     │───▶│  Processor   │   │
│  │    Agent     │    │   Decision   │    │    Agent     │   │
│  └──────────────┘    └──────┬───────┘    └──────────────┘   │
│                             │                                │
│                      ┌──────▼───────┐                       │
│                      │ Rectification│                       │
│                      │    Agent     │◀─────────────────┐    │
│                      └──────────────┘                  │    │
│                             │                          │    │
│                             └────── (re-submit) ───────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

1. **User Request** → Proposal Agent generates output
2. **Review** → User reviews in chat
3. **Decision**:
   - `approve` → Processor Agent executes
   - `reject: <reason>` → Rectification Agent fixes
4. **Loop** → Rectified output goes back for approval
5. **Complete** → Final execution after approval

## Quick Start

### 1. Install Dependencies

Before running any scripts, install the package so Python can import `hitl_agent`:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

Copy the example env file and fill in your values:

```bash
cp env_example.txt .env
```

Edit `.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE

# Service account credentials (required for Agent Engine)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Will be set after running setup_agent_engine.py
AGENT_ENGINE_ID=your-agent-engine-id
```

Alternatively, authenticate via gcloud CLI instead of a service account file:

```bash
gcloud auth application-default login
```

### 3. Create Agent Engine (for VertexAI services)

```bash
python setup_agent_engine.py
```

Add the returned `AGENT_ENGINE_ID` to your `.env` file.

### 4. Run Locally

```bash
uv run python run_local.py
```

### 5. Run with ADK Web UI

```bash
uv run adk web
```

Navigate to `http://localhost:8000`

## Chat Commands

When a proposal is presented, respond with:

| Command | Action |
|---------|--------|
| `approve` | Approve and proceed to next step |
| `yes`, `ok`, `lgtm` | Same as approve |
| `reject: <reason>` | Reject with feedback |
| `no: <reason>` | Same as reject |

### Examples

```
You: Write a Python function to calculate factorial

Agent: [Proposal Agent generates function]
   Proposal Ready for Review...
   
You: reject: Please add input validation and docstring

Agent: [Rectification Agent improves]
   Rectified Proposal Ready...
   
You: approve

Agent: Proposal approved! Executing...
```

## Deploy to Cloud Run

### 1. Build Container

```bash
docker build -t hitl-agent .
```

### 2. Push to Container Registry

```bash
# Tag for GCR
docker tag hitl-agent gcr.io/YOUR_PROJECT/hitl-agent

# Push
docker push gcr.io/YOUR_PROJECT/hitl-agent
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy hitl-agent \
  --image gcr.io/YOUR_PROJECT/hitl-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,AGENT_ENGINE_ID=your-engine-id,GOOGLE_CLOUD_PROJECT=your-project,GOOGLE_CLOUD_LOCATION=us-central1" \
  --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=vertex-service-account:latest" \
  --allow-unauthenticated
```

## 📁 Project Structure

```
hitl-adk/
├── hitl_agent/
│   ├── __init__.py      # Package exports
│   ├── agent.py         # Agent definitions
│   ├── tools.py         # HITL tools (approve/reject)
│   ├── callbacks.py     # Response parsing callbacks
│   ├── prompts.py       # System prompts
│   └── services.py      # VertexAI service configuration
├── run_local.py         # Local testing script
├── setup_agent_engine.py # Agent Engine setup
├── pyproject.toml       # Dependencies
├── Dockerfile           # Cloud Run deployment
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `TRUE` for VertexAI | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON (or use `gcloud auth`) | For Agent Engine |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Yes |
| `GOOGLE_CLOUD_LOCATION` | GCP region | Defaults to `us-central1` |
| `AGENT_ENGINE_ID` | Agent Engine ID for sessions/memory | Yes (after setup) |

### Using Local Services (No VertexAI)

For pure local testing without VertexAI, simply don't set `AGENT_ENGINE_ID`:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
# API key/service account not configured - uses InMemory services
```

## References

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [VertexAI Express Mode](https://google.github.io/adk-docs/sessions/express-mode/)
- [ADK Human-in-the-Loop Example](https://github.com/jackwotherspoon/adk-human-in-the-loop)

## 📄 License

Apache-2.0

