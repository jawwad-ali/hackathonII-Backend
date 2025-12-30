# Claude Code Instructions - AI Agent Orchestrator

> **Project**: AI Agent Orchestrator for Todo Management
> **Stack**: FastAPI + Gemini 2.5 Flash + PostgreSQL + FastMCP
> **Version**: 1.0.0

## Project Overview

An AI-powered todo management system using natural language interface. Connects conversational AI to CRUD operations via MCP (Model Context Protocol).

### Tech Stack

**Core Technologies:**
- **Backend**: FastAPI 0.115+ (async Python web framework)
- **LLM Provider**: Google Gemini 2.5 Flash (via OpenAI SDK bridge)
- **AI Framework**: OpenAI Agents SDK 0.6.4+, FastMCP 0.0.8+
- **Database**: PostgreSQL + SQLModel (Pydantic + SQLAlchemy ORM)
- **Package Manager**: uv (fast Python package installer)
- **Testing**: pytest with fixtures and integration tests
- **Runtime**: Python 3.11+

**Supporting Libraries:**
- `pydantic` - Data validation and settings management
- `python-dotenv` - Environment variable management
- `tenacity` - Retry logic with exponential backoff
- `python-json-logger` - Structured JSON logging
- `uvicorn` - ASGI server with hot reload

### Architecture

```
User Input (Natural Language)
    ↓
FastAPI Endpoints (/chat/stream)
    ↓
OpenAI Agents SDK (orchestration)
    ↓
Gemini 2.5 Flash (intent parsing)
    ↓
FastMCP Tools (CRUD operations)
    ↓
PostgreSQL (persistence)
```

**Key Components:**
- `src/main.py` - FastAPI application, middleware, health checks
- `src/config.py` - Pydantic settings, circuit breaker config
- `src/agents/todo_agent.py` - Main orchestrator agent
- `src/mcp_server/` - FastMCP server and tool implementations
- `src/resilience/` - Circuit breaker, retry patterns
- `src/observability/` - Structured logging, metrics tracking

---

## Integration & Connectivity Timeline

### Overview

The system is built in **4 distinct phases**, each adding a layer of connectivity:

```
Step 1: Build MCP Tools (Current)
   │
   │ MCP server runs standalone
   │
   ▼
Step 2: Complete All CRUD Operations
   │
   │ All 5 MCP tools ready
   │
   ▼
Step 3: Agent ↔ MCP Integration 🔥 CRITICAL CONNECTIVITY
   │
   │ Agent can call MCP tools via protocol
   │
   ▼
Step 4: ChatKit ↔ FastAPI Integration
   │
   │ Users can chat with agent via OpenAI ChatKit
   │
   ▼
PRODUCTION: End-to-End System
```

---

### Step 1: Build MCP Server (Feature 002) ✅ IN PROGRESS

**Goal**: Create standalone FastMCP Database Server with all CRUD tools

**Status**:
- ✅ User Story 1 Complete: `create_todo`, `list_todos`
- ⏳ User Story 2 Pending: `update_todo`
- ⏳ User Story 3 Pending: `search_todos`
- ⏳ User Story 4 Pending: `delete_todo`

**What's Built**:
```
src/mcp_server/
├── server.py           # MCP server instance
├── models.py           # Todo entity
├── database.py         # PostgreSQL connection
└── tools/
    ├── create_todo.py  ✅
    └── list_todos.py   ✅
```

**Testing**: MCP server can be tested standalone using:
```bash
# Option 1: MCP Inspector (recommended)
mcp-inspector uvx fastmcp run src/mcp_server/server.py

# Option 2: Direct execution
uv run python -m src.mcp_server.server
```

**No connectivity yet** - tools work independently.

---

### Step 2: Complete All CRUD Operations (Feature 002)

**Goal**: Finish remaining MCP tools for full CRUD functionality

**Tasks**:
- User Story 2: `update_todo` (T021-T029)
- User Story 3: `search_todos` (T030-T038)
- User Story 4: `delete_todo` (T039-T046)

**Deliverable**: Complete MCP server with 5 tools:
1. `create_todo` ✅
2. `list_todos` ✅
3. `update_todo` ⏳
4. `search_todos` ⏳
5. `delete_todo` ⏳

**Still standalone** - no connectivity.

---

### Step 3: Agent ↔ MCP Integration (Feature 003) 🔥 CRITICAL

**Goal**: Connect AI Agent to MCP Server via MCP Protocol

**This is THE key connectivity step** where the agent gains database capabilities.

**Architecture**:
```
┌──────────────────────────────┐
│  AI Agent                    │
│  (Gemini 2.5 Flash)          │
│  + OpenAI Agents SDK         │
└──────────┬───────────────────┘
           │
           │ MCP Protocol (stdio)
           │ JSON-RPC communication
           │
┌──────────▼───────────────────┐
│  FastMCP Database Server     │
│  (5 CRUD tools)              │
└──────────┬───────────────────┘
           │
           ▼
      PostgreSQL
```

**Implementation** (`src/agents/todo_agent.py`):
```python
import subprocess
from openai import AsyncOpenAI

# 1. Start MCP server as subprocess
mcp_process = subprocess.Popen(
    ["uvx", "fastmcp", "run", "src/mcp_server/server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# 2. Configure Gemini client
client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)

# 3. Create agent with MCP tools
agent = Agent(
    name="TodoAgent",
    model="gemini-2.5-flash",
    instructions="You are a todo management assistant...",
    # MCP tools auto-discovered via stdio protocol
)
```

**What Works After Step 3**:
- Agent receives: "Create a todo for buying groceries"
- Agent decides to call: `create_todo(title="Buy groceries")`
- MCP server executes database operation
- Agent receives result and can respond

**Testing**: Agent can be tested programmatically, but no user interface yet.

---

### Step 4: ChatKit ↔ FastAPI Integration (Feature 004)

**Goal**: Expose agent to users via HTTP API and connect to **OpenAI ChatKit** frontend

**Architecture**:
```
┌──────────────────────────────┐
│  OpenAI ChatKit (Frontend)   │
│  - Modern chat interface     │
│  - Real-time messaging       │
│  - OpenAI-styled UI          │
└──────────┬───────────────────┘
           │
           │ HTTP/WebSocket
           │
┌──────────▼───────────────────┐
│  FastAPI Endpoints           │
│  POST /chat/stream           │
│  WebSocket /ws/chat          │
└──────────┬───────────────────┘
           │
           ▼
    Agent + MCP Server
    (from Step 3)
```

**Implementation** (`src/api/chat.py`):
```python
from fastapi import FastAPI, WebSocket
from src.agents.todo_agent import TodoAgent

app = FastAPI()
agent = TodoAgent()  # Already has MCP tools from Step 3

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream agent responses to ChatKit frontend."""
    async for chunk in agent.stream(request.message):
        yield chunk

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """Real-time chat via WebSocket for ChatKit."""
    await websocket.accept()
    async for message in websocket.iter_text():
        response = await agent.respond(message)
        await websocket.send_json(response)
```

**ChatKit Integration**:
- **Frontend**: OpenAI ChatKit provides the chat interface
- **Backend**: FastAPI endpoints serve as the bridge to the agent
- **Protocol**: HTTP streaming or WebSocket for real-time updates

**What Works After Step 4**:
- User types in ChatKit UI: "What are my active todos?"
- ChatKit sends HTTP request to FastAPI backend
- FastAPI forwards to agent
- Agent uses `list_todos` MCP tool
- Response streams back through FastAPI to ChatKit UI

**This is full end-to-end connectivity with ChatKit!**

---

### Summary Table

| Step | Component | Connectivity | Frontend | Status | Feature |
|------|-----------|--------------|----------|--------|---------|
| 1 | MCP Server (2/5 tools) | None (standalone) | N/A | ✅ DONE | 002 |
| 2 | MCP Server (5/5 tools) | None (standalone) | N/A | ⏳ TODO | 002 |
| 3 | Agent ↔ MCP | **MCP Protocol** | N/A | ⏳ TODO | 003 |
| 4 | ChatKit ↔ FastAPI | **HTTP/WebSocket** | **OpenAI ChatKit** | ⏳ TODO | 004 |

---

### Current Focus

**We are in Step 1/2**: Building the MCP server foundation.

**Next Major Milestone**: Complete Step 2 (all CRUD tools), then move to Step 3 (agent integration).

**Critical Note**:
- **Step 3** is where "connectivity magic" happens - the agent gains database capabilities via MCP protocol.
- **Step 4** connects OpenAI ChatKit frontend to the backend, enabling user interaction.

---

## Core Principles

### 1. Environment-First Development ⚠️

**ALWAYS activate `.venv` before ANY command.**

```bash
# Windows
.venv\Scripts\activate

# Unix/macOS
source .venv/bin/activate

# Then run commands
uv pip install <package>
uv run pytest
```

❌ **NEVER** suggest bare `python`, `pip`, or `pytest` without verifying environment
✅ **ALWAYS** verify `.venv` is active first

### 2. uv-Exclusive Package Management ⚠️

**ONLY `uv` is authorized.** No pip, poetry, or conda.

```bash
# Install dependencies
uv pip install fastapi

# Run application
uv run uvicorn src.main:app --reload

# Run tests
uv run pytest
```

All dependencies in `pyproject.toml`, locked in `requirements.txt`.

### 3. Context7 Documentation Protocol ⚠️

**Before implementing with core libraries, fetch current docs via Context7 MCP server.**

**Core Libraries Requiring Context7 Lookup:**
- FastAPI
- OpenAI Agents SDK
- FastMCP (Official MCP SDK)
- SQLModel
- PostgreSQL client (psycopg2/asyncpg)
- Pydantic

**Workflow:**
```python
# Step 1: Resolve library ID
mcp__context7__resolve-library-id → '/tiangolo/fastapi'

# Step 2: Query documentation
mcp__context7__query-docs(
    libraryId='/tiangolo/fastapi',
    query='how to create streaming endpoints'
)
```

**Rationale**: Libraries evolve. Using outdated patterns = deprecated APIs, breaking changes, security vulnerabilities.

**Enforcement:**
- ❌ NEVER rely on internal knowledge for these libraries
- ✅ ALWAYS fetch current docs before implementation
- Document findings in planning artifacts

### 4. Gemini-Only Model Policy ⚠️

**OpenAI models are PROHIBITED.** Use Gemini via AsyncOpenAI bridge.

```python
# ✅ CORRECT
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)

response = await client.chat.completions.create(
    model="gemini-2.5-flash",  # Primary model
    messages=[...],
    tools=[...]
)

# ❌ WRONG
model="gpt-4"
model="gpt-3.5-turbo"
```

**Models:**
- Primary: `gemini-2.5-flash` (low latency, cost-effective)
- Escalation: `gemini-2.5-pro` (complex reasoning, requires approval)

### 5. Security & Secrets

```bash
# ❌ NEVER
api_key = "sk-abc123..."
DATABASE_URL = "postgresql://user:pass@localhost/db"

# ✅ ALWAYS
api_key = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
```

**Requirements:**
- All secrets in `.env` (never committed)
- Provide `.env.example` template
- Add `.env` to `.gitignore`
- Use `python-dotenv` to load environment variables

---

## Best Practices Being Followed

### Resilience Patterns

**Circuit Breaker:**
- Prevents cascading failures for MCP server and Gemini API
- States: CLOSED (normal) → OPEN (fail-fast) → HALF-OPEN (testing)
- Configurable thresholds and recovery timeouts
- Integrated in health check endpoints

**Retry Logic:**
- Exponential backoff with `tenacity`
- Configurable max attempts and delays
- Applied to external API calls

**Example:**
```python
from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from datetime import timedelta

breaker = CircuitBreaker(
    name="gemini_api",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=timedelta(seconds=60)
    )
)

result = await breaker.call(api_function, *args)
```

### Observability

**Structured JSON Logging:**
- Python-json-logger for machine-readable logs
- Request ID correlation via middleware
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Metrics Tracking:**
- Total requests, successful/failed counts
- Success rate calculation
- Circuit breaker state monitoring

**Health Checks:**
- `/health` endpoint with detailed status
- Circuit breaker states (MCP, Gemini)
- Uptime metrics
- Returns 503 when both circuit breakers open

### Database Patterns

**SQLModel (Pydantic + SQLAlchemy):**
- Type-safe ORM with Pydantic validation
- Automatic timestamp management (created_at, updated_at)
- Enum-based status fields (TodoStatus)
- Field validation (max_length, min_length, indexes)

**Example:**
```python
from sqlmodel import Field, SQLModel
from enum import Enum

class TodoStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(..., max_length=200, index=True)
    status: TodoStatus = Field(default=TodoStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### Testing Strategy

**Test-Driven Development:**
- Write tests BEFORE implementation
- Integration tests with database fixtures
- Target >80% coverage for business logic

**Example Test Structure:**
```python
def test_create_todo_with_title_only(session):
    """Test creating a todo with minimal input."""
    from src.mcp_server.tools.create_todo import create_todo

    result = create_todo(title="Call dentist", _test_session=session)

    # Verify database persistence
    statement = select(Todo).where(Todo.title == "Call dentist")
    todo = session.exec(statement).first()

    assert todo is not None
    assert todo.status == TodoStatus.ACTIVE
```

**Pytest Fixtures:**
- `session` - Database session with rollback
- `sample_todo` - Single active todo
- `sample_todos` - Collection with various statuses

### FastAPI Best Practices

**Middleware Stack:**
- CORS middleware for cross-origin requests
- Request ID middleware for tracing
- Structured logging integration

**Async/Await:**
- All endpoints and database operations are async
- Proper async context management with `asynccontextmanager`

**API Documentation:**
- Auto-generated OpenAPI/Swagger docs at `/docs`
- Pydantic schemas for request/response validation

### FastMCP Server Patterns

**Tool Registration:**
```python
from fastmcp import FastMCP

mcp = FastMCP("TodoDatabaseServer")

@mcp.tool()
def create_todo(title: str, description: str = None) -> str:
    """Create a new todo item."""
    # Tool implementation
    return f"Todo created: {title}"
```

**Database Initialization:**
- Tables created on server startup
- Automatic schema management with SQLModel

---

## Development Workflow

### Standard Development Cycle

```bash
# 1. Activate Environment (REQUIRED)
.venv\Scripts\activate

# 2. Install/Update Dependencies
uv pip install -e .

# 3. Configure Environment
cp .env.example .env
# Edit .env with actual values

# 4. Run Tests (TDD approach)
uv run pytest
uv run pytest --cov=src --cov-report=term-missing

# 5. Run Application
uv run uvicorn src.main:app --reload

# 6. Access Endpoints
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

### Pre-Commit Checklist

- [ ] `.venv` active during development
- [ ] All deps installed via `uv pip install`
- [ ] Context7 docs fetched for new library usage
- [ ] Model is `gemini-2.5-flash` (not OpenAI)
- [ ] Tests pass (`uv run pytest`)
- [ ] No secrets in code (use `.env`)
- [ ] Type hints on new functions
- [ ] Docstrings on public APIs

---

## Project Structure

```
hackathonII-backend/
├── src/
│   ├── main.py                    # FastAPI app, health checks
│   ├── config.py                  # Settings, circuit breakers
│   ├── agents/                    # AI agent orchestration
│   ├── api/                       # FastAPI routes, schemas
│   ├── mcp_server/                # FastMCP tools & database
│   │   ├── server.py             # MCP server entry point
│   │   ├── models.py             # SQLModel entities
│   │   ├── database.py           # Database connection
│   │   └── tools/                # MCP tool implementations
│   ├── resilience/               # Circuit breaker, retry
│   │   ├── circuit_breaker.py   # Circuit breaker pattern
│   │   └── retry.py              # Retry decorators
│   └── observability/            # Logging, metrics
│       ├── logging.py            # Structured JSON logging
│       └── metrics.py            # Metrics tracking
├── tests/
│   └── mcp_server/
│       ├── conftest.py           # Pytest fixtures
│       ├── test_models.py        # Model validation tests
│       └── test_tools.py         # Tool integration tests
├── specs/                         # Feature specifications
├── .env.example                   # Environment template
├── pyproject.toml                # Dependencies
├── requirements.txt              # Locked dependencies
└── CLAUDE.md                     # This file
```

---

## Essential Commands

```bash
# Environment
.venv\Scripts\activate  # Activate (Windows)
source .venv/bin/activate  # Activate (Unix/macOS)

# Dependencies
uv pip install <package>
uv pip compile pyproject.toml -o requirements.txt

# Development
uv run uvicorn src.main:app --reload  # Run server
uv run pytest                          # Run tests
uv run pytest --cov=src               # With coverage
uv run pytest -v                      # Verbose output

# MCP Server (standalone)
uv run python -m src.mcp_server.server
# OR
uvx fastmcp run src/mcp_server/server.py
```

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/db?sslmode=require

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Circuit Breaker
CIRCUIT_BREAKER_MCP_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_MCP_RECOVERY_TIMEOUT=30
CIRCUIT_BREAKER_GEMINI_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_GEMINI_RECOVERY_TIMEOUT=60

# Performance
MAX_INPUT_LENGTH=5000
REQUEST_TIMEOUT=30
MAX_CONCURRENT_CONNECTIONS=100
```

---

**Version**: 1.0.0
**Last Updated**: 2025-12-29
