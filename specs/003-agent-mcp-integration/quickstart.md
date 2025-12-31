# Quickstart Guide: Agent-MCP Integration

**Feature**: 003-agent-mcp-integration
**Date**: 2025-12-31
**Audience**: Developers setting up and testing the Agent-MCP integration locally

## Overview

This guide walks you through setting up, running, and testing the integrated AI-driven Todo application. By the end, you'll have:
- FastAPI server running with TodoAgent connected to FastMCP Database Server
- Ability to create, list, update, search, and delete todos via natural language
- Real-time streaming responses showing tool execution

**Time to complete**: ~15 minutes

---

## Prerequisites

- **Python**: 3.11 or higher
- **uv**: Fast Python package manager ([install guide](https://github.com/astral-sh/uv))
- **PostgreSQL**: Running instance (local or cloud like Neon)
- **Gemini API Key**: From Google AI Studio
- **Git**: Version control

### Check Prerequisites

```bash
python --version  # Should show 3.11+
uv --version      # Should show uv installed
psql --version    # Should show PostgreSQL installed
```

---

## Step 1: Environment Setup

### 1.1 Clone Repository

```bash
git clone <repository-url>
cd hackathonII-Backend
git checkout 003-agent-mcp-integration
```

### 1.2 Create Virtual Environment

```bash
# Create .venv
uv venv

# Activate (REQUIRED before any commands)
# Windows:
.venv\Scripts\activate

# Unix/macOS:
source .venv/bin/activate
```

### 1.3 Install Dependencies

```bash
# Install all dependencies via uv
uv pip install -e .

# Verify installation
uv pip list | grep fastapi
uv pip list | grep openai
uv pip list | grep fastmcp
```

---

## Step 2: Configuration

### 2.1 Create Environment File

```bash
# Copy example
cp .env.example .env

# Edit .env with your values
```

### 2.2 Configure Environment Variables

Edit `.env`:

```env
# Database (update with your PostgreSQL URL)
DATABASE_URL=postgresql://user:password@localhost:5432/todo_db

# Gemini API (update with your API key)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash

# MCP Server
MCP_SERVER_COMMAND=uvx
MCP_SERVER_ARGS=["fastmcp", "run", "src/mcp_server/server.py"]
MCP_SERVER_TIMEOUT=5

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Circuit Breaker
CIRCUIT_BREAKER_MCP_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_MCP_RECOVERY_TIMEOUT=30
CIRCUIT_BREAKER_GEMINI_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_GEMINI_RECOVERY_TIMEOUT=60
```

### 2.3 Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE todo_db;

# Exit
\q
```

**Note**: Database tables are created automatically by SQLModel on first run.

---

## Step 3: Verify MCP Server

Before starting FastAPI, verify the FastMCP server works standalone.

### 3.1 Test MCP Server Directly

```bash
# Run MCP server in standalone mode
uv run python -m src.mcp_server.server
```

Expected output:
```
INFO: FastMCP server starting...
INFO: Database tables created
INFO: 5 tools registered: create_todo, list_todos, update_todo, search_todos, delete_todo
INFO: Server ready on stdio
```

Press `Ctrl+C` to stop.

### 3.2 Inspect MCP Server Schema (Optional)

```bash
# Use MCP Inspector to verify tool schemas
uvx fastmcp inspect src/mcp_server/server.py
```

Expected output:
- Server name: "TodoDatabaseServer"
- 5 tools with descriptions and parameter schemas

---

## Step 4: Start FastAPI Server

### 4.1 Run Server

```bash
# Start with hot reload (development)
uv run uvicorn src.main:app --reload

# Or without reload (production-like)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Expected startup output:
```
INFO: MCP server connecting...
INFO: MCP server connected successfully
INFO: Discovered 5 tools from MCP server
INFO: TodoAgent initialized with MCP tools
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 4.2 Verify Server Health

Open browser or use `curl`:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "uptime": 12.34,
  "circuit_breakers": {
    "mcp": {
      "state": "CLOSED",
      "failure_count": 0
    },
    "gemini": {
      "state": "CLOSED",
      "failure_count": 0
    }
  },
  "metrics": {
    "total_requests": 1,
    "successful_requests": 1,
    "failed_requests": 0,
    "success_rate": 1.0
  }
}
```

**Health Check States**:
- `status: "healthy"` - All systems operational
- `status: "degraded"` - MCP circuit breaker open (Gemini working)
- `status: "critical"` - Gemini circuit breaker open (returns HTTP 503)

---

## Step 5: Test Chat Endpoint

### 5.1 Create a Todo (Natural Language)

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a task to buy groceries",
    "request_id": "req_001"
  }'
```

Expected SSE stream:
```
event: THINKING
data: {"content": "I'll create a todo for buying groceries"}

event: TOOL_CALL
data: {"tool_name": "create_todo", "status": "IN_PROGRESS", "args": {"title": "Buy groceries"}}

event: TOOL_CALL
data: {"tool_name": "create_todo", "status": "COMPLETED", "result": {"id": 1, "title": "Buy groceries", "status": "active"}}

event: RESPONSE_DELTA
data: {"text": "I've created a todo for buying groceries with ID 1."}

event: DONE
data: {"final_output": "I've created a todo for buying groceries with ID 1."}
```

### 5.2 List Todos

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are my active todos?",
    "request_id": "req_002"
  }'
```

Expected response (streamed):
```
event: THINKING
data: {"content": "I'll list active todos"}

event: TOOL_CALL
data: {"tool_name": "list_todos", "status": "IN_PROGRESS", "args": {"status": "active"}}

event: TOOL_CALL
data: {"tool_name": "list_todos", "status": "COMPLETED", "result": [{"id": 1, "title": "Buy groceries", "status": "active"}]}

event: RESPONSE_DELTA
data: {"text": "You have 1 active todo:\n1. Buy groceries (ID: 1)"}

event: DONE
data: {"final_output": "You have 1 active todo:\n1. Buy groceries (ID: 1)"}
```

### 5.3 Update a Todo

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Mark todo 1 as completed",
    "request_id": "req_003"
  }'
```

### 5.4 Search Todos

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for tasks related to groceries",
    "request_id": "req_004"
  }'
```

### 5.5 Delete a Todo

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Delete todo 1",
    "request_id": "req_005"
  }'
```

---

## Step 6: Test Degraded Mode

Simulate MCP server failure to verify graceful degradation.

### 6.1 Stop MCP Server (Simulate Failure)

In a separate terminal:

```bash
# Find MCP server process
ps aux | grep fastmcp

# Kill process
kill <process_id>
```

### 6.2 Send Request During Downtime

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new task",
    "request_id": "req_degraded"
  }'
```

Expected response (HTTP 200):
```json
{
  "error": "Todo database is temporarily unavailable. Please try again later.",
  "status": "degraded"
}
```

### 6.3 Check Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response (HTTP 200):
```json
{
  "status": "degraded",
  "circuit_breakers": {
    "mcp": {
      "state": "OPEN",
      "failure_count": 5
    },
    "gemini": {
      "state": "CLOSED",
      "failure_count": 0
    }
  }
}
```

**Note**: Server returns HTTP 200 with `status: "degraded"` (not HTTP 503) per SC-013.

---

## Step 7: Explore API Documentation

### 7.1 Interactive API Docs

Open browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 7.2 Available Endpoints

- `GET /` - API information
- `GET /health` - Health check with circuit breaker status
- `POST /chat/stream` - Chat with TodoAgent (SSE streaming)

---

## Step 8: View Logs

Logs use structured JSON format for observability.

### 8.1 Tail Logs

```bash
# Application logs (if using file logging)
tail -f logs/app.log

# Or view console output (default)
# Logs appear in terminal where uvicorn is running
```

### 8.2 Log Format

```json
{
  "timestamp": "2025-12-31T10:30:15Z",
  "level": "INFO",
  "message": "MCP tool call completed",
  "request_id": "req_001",
  "tool_name": "create_todo",
  "duration": 0.345,
  "status": "success"
}
```

---

## Step 9: Run Tests

Verify integration with automated tests.

### 9.1 Run All Tests

```bash
uv run pytest
```

### 9.2 Run Integration Tests Only

```bash
uv run pytest tests/integration/
```

### 9.3 Run with Coverage

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Expected output:
```
========================== test session starts ==========================
collected 15 items

tests/integration/test_mcp_connection.py ....          [ 26%]
tests/integration/test_agent_tools.py .......          [ 73%]
tests/integration/test_streaming.py ....               [100%]

========================== 15 passed in 12.34s ==========================

---------- coverage: platform win32, python 3.11.0 ----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
src/agents/todo_agent.py             45      3    93%   42-44
src/api/routes.py                    67      5    93%   89-92, 105
src/mcp/client.py                    38      2    95%   67-68
---------------------------------------------------------------
TOTAL                               150     10    93%
```

---

## Step 10: Common Issues & Troubleshooting

### Issue: "MCP server connection failed"

**Symptom**: Server starts but logs show MCP connection error.

**Solutions**:
1. Verify `DATABASE_URL` in `.env` is correct
2. Ensure PostgreSQL is running: `pg_isready`
3. Check MCP server runs standalone: `uv run python -m src.mcp_server.server`
4. Review logs for specific error messages

### Issue: "Gemini API error"

**Symptom**: Chat requests fail with Gemini-related errors.

**Solutions**:
1. Verify `GEMINI_API_KEY` in `.env` is valid
2. Check API quota: https://aistudio.google.com/apikey
3. Test API key with direct request:
   ```bash
   curl -X POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent \
     -H "x-goog-api-key: $GEMINI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents": [{"parts": [{"text": "Hello"}]}]}'
   ```

### Issue: "Circuit breaker open"

**Symptom**: Health check shows circuit breaker in OPEN state.

**Solutions**:
1. Wait for recovery timeout (30s for MCP, 60s for Gemini)
2. Circuit breaker transitions to HALF-OPEN automatically
3. Next successful request closes circuit breaker
4. Check logs for root cause of failures

### Issue: "ModuleNotFoundError"

**Symptom**: Import errors when running server.

**Solutions**:
1. Ensure `.venv` is activated: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
2. Reinstall dependencies: `uv pip install -e .`
3. Verify Python version: `python --version` (must be 3.11+)

---

## Next Steps

### Integrate with ChatKit Frontend

1. Deploy FastAPI backend to production (e.g., Render, Railway)
2. Configure ChatKit frontend to connect to backend endpoint
3. Enable CORS for ChatKit domain in `src/main.py` (already configured for all origins)

### Production Deployment

1. Switch to SSE transport for networked MCP server:
   - Update `.env` to use SSE configuration
   - Deploy MCP server as separate service
2. Enable production logging:
   - Configure log aggregation (e.g., Loki, CloudWatch)
3. Monitor metrics:
   - Track circuit breaker states via `/health` endpoint
   - Set up alerts for degraded mode
4. Scale horizontally:
   - Multiple FastAPI instances behind load balancer
   - Each instance spawns own MCP server subprocess (stdio)
   - Or shared MCP server via SSE (recommended for production)

### Advanced Features

- Add authentication (user_id in tool call context)
- Implement conversation history persistence
- Add rate limiting per user
- Enable multi-tenant todo isolation

---

## Useful Commands Reference

```bash
# Environment
.venv\Scripts\activate              # Activate (Windows)
source .venv/bin/activate           # Activate (Unix)

# Dependencies
uv pip install -e .                 # Install project
uv pip list                         # List installed packages

# Development
uv run uvicorn src.main:app --reload  # Run with hot reload
uv run pytest                         # Run tests
uv run pytest --cov=src              # Run with coverage

# MCP Server
uv run python -m src.mcp_server.server     # Run standalone
uvx fastmcp inspect src/mcp_server/server.py  # Inspect schema

# Database
psql -U postgres -c "CREATE DATABASE todo_db;"  # Create DB
psql -U postgres todo_db -c "SELECT * FROM todos;"  # Query todos

# Logs
tail -f logs/app.log                # Tail logs (if file logging enabled)
```

---

## Support

- **Documentation**: See `CLAUDE.md` for project guidelines
- **Issues**: Create GitHub issue for bugs/feature requests
- **Logs**: Structured JSON logs provide detailed debugging information

---

**Quickstart Status**: ✅ COMPLETE - Ready for user onboarding
