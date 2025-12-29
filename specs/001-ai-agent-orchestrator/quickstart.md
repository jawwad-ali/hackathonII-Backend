# Quickstart Guide: AI Agent Orchestrator

**Feature**: 001-ai-agent-orchestrator
**Target Audience**: Developers implementing this feature

This guide walks you through setting up and running the AI Agent Orchestrator locally.

## Prerequisites

- **Python**: 3.11 or higher (REQUIRED per clarifications)
- **Docker**: For containerized deployment (REQUIRED per clarifications)
- **uv**: Package manager (install: `pip install uv`)
- **Google Gemini API Key**: For Gemini 2.5 Flash model
- **External MCP Server**: Running FastMCP todo server (separate service)
- **Git**: For version control

---

## Step 1: Environment Setup

### 1.1 Activate Virtual Environment

**CRITICAL**: Always verify `.venv` is active before any commands (Constitution requirement).

**Windows**:
```powershell
.venv\Scripts\activate
```

**Unix/macOS**:
```bash
source .venv/bin/activate
```

**Verify**:
```bash
which python  # Should point to .venv/bin/python or .venv\Scripts\python
```

### 1.2 Install Dependencies

```bash
# Install all dependencies via uv (ONLY package manager allowed)
uv pip install -e .

# Or if using requirements.txt
uv pip install -r requirements.txt
```

**Expected dependencies** (from pyproject.toml):
```toml
[project.dependencies]
fastapi = "^0.115.0"
openai-agents-python = "latest"
agents-mcp = "latest"
openai = "latest"  # For AsyncOpenAI
pydantic = "^2.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
python-dotenv = "^1.0"

[project.optional-dependencies.dev]
pytest = "^8.0"
pytest-asyncio = "^0.24.0"
httpx = "^0.27.0"
```

### 1.3 Docker Setup (Alternative - RECOMMENDED for Production)

**NEW from Clarifications**: Docker containerization is required for production deployment.

**Build the Docker image**:
```bash
# Multi-stage build for optimized image size
docker build -t ai-agent-orchestrator:latest .
```

**Run with Docker Compose** (includes MCP server):
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f orchestrator

# Stop services
docker-compose down
```

**docker-compose.yml example**:
```yaml
version: '3.8'

services:
  orchestrator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
      - MCP_SERVER_URL=http://mcp-server:5000
      - LOG_LEVEL=INFO
    depends_on:
      - mcp-server
    restart: unless-stopped

  mcp-server:
    image: fastmcp-todo-server:latest
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/todos
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=todos
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

**Dockerfile example** (multi-stage build):
```dockerfile
# Build stage
FROM python:3.11-slim-bookworm AS builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Runtime stage
FROM python:3.11-slim-bookworm
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ ./src/
COPY mcp_agent.config.yaml ./
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Step 2: Configuration

### 2.1 Environment Variables

Create `.env` file in project root:

```env
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash

# MCP Server Configuration
MCP_TODO_SERVER_COMMAND=uvx
MCP_TODO_SERVER_ARGS=fastmcp,run,path/to/todo_server.py

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Optional: For future multi-user support
# JWT_SECRET=your_jwt_secret
```

**IMPORTANT**: Never commit `.env` to version control. Use `.env.example` as template.

### 2.2 MCP Agent Configuration

Create `mcp_agent.config.yaml` in project root:

```yaml
$schema: "https://raw.githubusercontent.com/lastmile-ai/mcp-agent/main/schema/mcp-agent.config.schema.json"

mcp:
  servers:
    todo_server:
      command: "uvx"
      args: ["fastmcp", "run", "path/to/todo_server.py"]
```

**Note**: Replace `path/to/todo_server.py` with actual path to your FastMCP server script.

---

## Step 3: Verify External Dependencies

### 3.1 Check MCP Server

Ensure the external FastMCP todo server is running:

```bash
# In separate terminal (in MCP server project directory)
uvx fastmcp run todo_server.py
```

**Expected output**:
```
FastMCP server running on http://localhost:5000
Available tools: create_todo, list_todos, update_todo, delete_todo
```

### 3.2 Test Gemini API Connection

```python
# test_gemini.py
from openai import AsyncOpenAI
import os
import asyncio

async def test_gemini():
    client = AsyncOpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url=os.getenv("GEMINI_BASE_URL")
    )

    response = await client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    print(response.choices[0].message.content)

asyncio.run(test_gemini())
```

Run:
```bash
uv run python test_gemini.py
```

**Expected output**: A greeting from Gemini model.

---

## Step 4: Run the Application

### 4.1 Start FastAPI Server

```bash
# Ensure .venv is active!
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 4.2 Verify Health Check

```bash
curl http://localhost:8000/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-21T12:00:00Z",
  "mcp_connection": true,
  "gemini_connection": true
}
```

---

## Step 5: Test Streaming Endpoint

### 5.1 Create Todo via Natural Language

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Remind me to buy eggs tomorrow at 3pm",
    "conversation_id": "test_conv_001"
  }'
```

**Expected SSE stream**:
```
event: thinking
data: {"content": "User wants to create a todo for buying eggs tomorrow at 3pm"}

event: tool_call
data: {"tool_name": "create_todo", "arguments": {"title": "buy eggs", "due_date": "2025-12-22T15:00:00", "priority": "medium"}, "status": "in_progress"}

event: response_delta
data: {"delta": "I've created a todo to ", "accumulated": "I've created a todo to "}

event: response_delta
data: {"delta": "buy eggs", "accumulated": "I've created a todo to buy eggs"}

event: done
data: {"final_output": "I've created a todo to buy eggs tomorrow at 3pm.", "tools_called": ["create_todo"], "success": true}
```

### 5.2 Query Todos

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What's on my todo list for today?"
  }'
```

### 5.3 Update Todo

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Mark the buy eggs task as complete"
  }'
```

---

## Step 6: Run Tests

### 6.1 Unit Tests

```bash
# Ensure .venv is active!
uv run pytest tests/unit -v
```

### 6.2 Integration Tests

```bash
# Requires MCP server running
uv run pytest tests/integration -v
```

### 6.3 Contract Tests

```bash
# Test ChatKit protocol compliance
uv run pytest tests/contract -v
```

### 6.4 Logging Verification (NEW)

**Verify structured JSON logging output**:

```bash
# Run a test request and check logs
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# Check logs (JSON format)
tail -f logs/app.log | jq
```

**Expected log entry format**:
```json
{
  "timestamp": "2025-12-21T12:00:00.123Z",
  "level": "INFO",
  "request_id": "req_abc123xyz",
  "event": "request_received",
  "details": {
    "method": "POST",
    "path": "/chat/stream",
    "input_length": 10
  }
}
```

**Verify request ID correlation**:
```bash
# Extract request ID from response header
curl -i -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}' | grep X-Request-ID

# Search logs by request ID
grep "req_abc123xyz" logs/app.log | jq
```

### 6.5 Circuit Breaker Testing (NEW)

**Simulate MCP server failure**:

```bash
# Stop MCP server
docker-compose stop mcp-server

# Send request (should fail with circuit breaker)
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# Expected: Error event after retries
```

**Check circuit breaker state**:
```bash
curl http://localhost:8000/health | jq
```

**Expected response (degraded state)**:
```json
{
  "status": "degraded",
  "timestamp": "2025-12-21T12:00:00Z",
  "circuit_breakers": {
    "mcp_server": {
      "state": "open",
      "failure_count": 5,
      "last_failure": "2025-12-21T11:59:45Z"
    },
    "gemini_api": {
      "state": "closed",
      "failure_count": 0,
      "last_failure": null
    }
  }
}
```

**Restart MCP server and verify recovery**:
```bash
# Restart MCP server
docker-compose start mcp-server

# Wait 30 seconds (recovery timeout)
sleep 30

# Check health (should transition to half-open, then closed)
curl http://localhost:8000/health | jq '.circuit_breakers.mcp_server.state'
# Expected: "half_open" or "closed"
```

---

## Project Structure Reference

```
hackathonII-Backend/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Environment configuration
│   ├── agents/
│   │   ├── todo_agent.py          # OpenAI Agents SDK agent
│   │   └── tool_definitions.py   # MCP tool schemas
│   ├── api/
│   │   ├── routes.py              # /chat/stream endpoint
│   │   └── schemas.py             # Pydantic models
│   ├── mcp/
│   │   └── client.py              # MCP integration (agents_mcp)
│   └── streaming/
│       └── chatkit.py             # SSE event formatting
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── specs/
│   └── 001-ai-agent-orchestrator/
│       ├── spec.md
│       ├── plan.md
│       ├── research.md
│       ├── data-model.md
│       ├── quickstart.md          # This file
│       └── contracts/
├── .env                           # Environment variables (DO NOT COMMIT)
├── .env.example                   # Template for .env
├── mcp_agent.config.yaml          # MCP server configuration
├── pyproject.toml                 # uv dependencies
└── README.md
```

---

## Common Issues & Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'agents'"

**Cause**: Virtual environment not activated or dependencies not installed.

**Solution**:
```bash
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/macOS
uv pip install -e .
```

### Issue 2: "MCP server connection failed"

**Cause**: External MCP server not running or incorrect configuration.

**Solution**:
1. Verify MCP server is running: `curl http://localhost:5000/health`
2. Check `mcp_agent.config.yaml` has correct command and args
3. Check `.env` has correct MCP configuration

### Issue 3: "Gemini API authentication failed"

**Cause**: Invalid or missing `GEMINI_API_KEY`.

**Solution**:
1. Verify API key in `.env`
2. Check `GEMINI_BASE_URL` is correct
3. Test API key: `uv run python test_gemini.py`

### Issue 4: "StreamingResponse not streaming"

**Cause**: Not using async generator or incorrect media type.

**Solution**:
- Ensure endpoint uses `async def generate_stream():`
- Set `media_type="text/event-stream"`
- Check SSE format: `event: <type>\ndata: <json>\n\n`

---

## Next Steps

1. **Implement Core Features**: Follow tasks.md for implementation order
2. **Add Tests**: Write tests for each user story (spec.md)
3. **ChatKit Integration**: Implement event mapping in `src/streaming/chatkit.py`
4. **Error Handling**: Add graceful degradation for MCP/Gemini failures
5. **Performance**: Add request timeout and concurrency limits

---

## Useful Commands Cheat Sheet

```bash
# Environment
.venv\Scripts\activate                          # Activate (Windows)
source .venv/bin/activate                       # Activate (Unix/macOS)

# Dependencies
uv pip install -e .                             # Install project
uv pip install <package>                        # Add dependency
uv pip list                                     # List installed packages

# Run
uv run uvicorn src.main:app --reload            # Start dev server
uv run python -m pytest                         # Run all tests
uv run python -m pytest -k test_name            # Run specific test

# MCP
uvx fastmcp run path/to/server.py               # Start MCP server
curl http://localhost:5000/tools                # List MCP tools

# Debugging
uv run python -m pdb src/main.py                # Debug mode
tail -f logs/app.log                            # Watch logs
```

---

## Constitution Compliance Checklist

Before implementation:
- [ ] `.venv` activation verified in all commands
- [ ] All dependencies installed via `uv` (not pip/poetry)
- [ ] MCP documentation fetched for all libraries
- [ ] AsyncOpenAI configured with Gemini base_url
- [ ] Model is `gemini-2.5-flash` (not OpenAI models)
- [ ] Tests written for all user stories
- [ ] `.env` added to `.gitignore`
- [ ] Skills executed (`/sp.specify`, `/sp.plan`, `/sp.tasks`)

---

**For questions or issues**, refer to:
- `specs/001-ai-agent-orchestrator/plan.md` - Architecture decisions
- `specs/001-ai-agent-orchestrator/research.md` - Technology research findings
- `specs/001-ai-agent-orchestrator/data-model.md` - Data contracts
- `.specify/memory/constitution.md` - Project principles
