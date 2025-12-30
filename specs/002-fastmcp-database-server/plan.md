# Implementation Plan: FastMCP Database Server for Todo Management

**Branch**: `002-fastmcp-database-server` | **Date**: 2025-12-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-fastmcp-database-server/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a FastMCP-based Database Server that provides MCP-compliant tools for Todo management (create, list, update, delete, search) with PostgreSQL persistence via SQLModel and psycopg2. This server acts as the data layer between the AI Agent Orchestrator and the database, exposing all CRUD operations as standardized MCP tools.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- FastMCP (Official Python SDK for MCP servers)
- SQLModel 0.0.24+ (ORM with Pydantic integration)
- psycopg2 2.9+ (PostgreSQL adapter - synchronous driver)
- PostgreSQL 14+ (Database)
- Pydantic 2.x (Data validation)

**MCP Documentation References**:
- psycopg2: `/psycopg/psycopg2` - Connection management, transaction handling, thread-safe connection pooling
- SQLModel: `/fastapi/sqlmodel` - Database engine creation, ORM models, session management

**Storage**: PostgreSQL with SQLModel ORM
**Database Driver**: psycopg2 (synchronous, thread-safe with connection pooling)
**Database URL Format**: `postgresql://username:password@host:port/database` (psycopg2 format, NOT asyncpg)
**Testing**: pytest with SQLModel test fixtures
**Target Platform**: Linux/Windows server (Python runtime)
**Project Type**: Single MCP server application
**Performance Goals**:
- <500ms response time for CRUD operations under normal load
- Support 100+ concurrent tool invocations without data corruption
- Connection pool: 2-10 connections (min-max)

**Constraints**:
- All tools MUST return MCP-compliant Content objects
- Title max 200 characters, description max 2000 characters
- Atomic operations (no partial updates)
- Thread-safe connection management

**Scale/Scope**:
- 5 MCP tools (create, list, update, delete, search)
- Single SQLModel entity (Todo)
- Support for 10k+ todo items
- Multi-threaded AI agent access

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Environment-First Rule ✅
- **Status**: PASS
- **Evidence**: All commands will be executed with `.venv` activated
- **Enforcement**: Development workflow requires environment activation before any uv commands

### Source of Truth Protocol (MCP) ✅
- **Status**: PASS
- **Evidence**:
  - psycopg2 docs fetched from `/psycopg/psycopg2` (connection patterns, pooling, transaction management)
  - SQLModel docs fetched from `/fastapi/sqlmodel` (engine creation, ORM patterns)
  - FastMCP docs to be fetched during Phase 0 research
- **Enforcement**: All implementation will reference MCP-fetched documentation, not internal knowledge

### Pre-Flight Skills Requirement ✅
- **Status**: PASS
- **Evidence**: Currently executing `/sp.plan` skill (Phase 1 of planning workflow)
- **Prerequisites**: `/sp.specify` already completed (spec.md exists)
- **Next Steps**: `/sp.tasks` after plan completion

### uv-Exclusive Package Management ✅
- **Status**: PASS
- **Evidence**: All dependencies managed via `pyproject.toml` and `uv pip install`
- **Enforcement**: No pip, poetry, or conda commands will be used

### Model & Connectivity Architecture ⚠️
- **Status**: NOT APPLICABLE (this feature)
- **Rationale**: This is the MCP Database Server - it does NOT interact with LLMs. The AI Agent Orchestrator (separate feature) handles Gemini connectivity.

### Test-First Development ✅
- **Status**: PASS
- **Evidence**: Plan includes pytest test structure for CRUD operations
- **Target**: >80% coverage for database operations and MCP tools

### Complexity Tracking
No constitutional violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/002-fastmcp-database-server/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0 output (to be created)
├── data-model.md        # Phase 1 output (to be created)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
│   └── mcp-tools.json   # MCP tool schemas
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
src/
├── mcp_server/          # NEW: FastMCP Database Server
│   ├── __init__.py
│   ├── server.py        # FastMCP server entry point
│   ├── models.py        # SQLModel Todo entity
│   ├── database.py      # Database engine, session, connection pool
│   ├── tools/           # MCP tool implementations
│   │   ├── __init__.py
│   │   ├── create_todo.py
│   │   ├── list_todos.py
│   │   ├── update_todo.py
│   │   ├── delete_todo.py
│   │   └── search_todos.py
│   └── config.py        # Database configuration
│
├── agents/              # EXISTING: AI Agent Orchestrator (separate feature)
│   ├── todo_agent.py
│   └── tool_definitions.py
│
└── config.py            # EXISTING: Global configuration

tests/
├── mcp_server/          # NEW: MCP server tests
│   ├── __init__.py
│   ├── conftest.py      # Pytest fixtures (test DB engine, sessions)
│   ├── test_models.py   # Todo model validation tests
│   ├── test_database.py # Connection pool, transaction tests
│   └── test_tools/      # MCP tool tests
│       ├── test_create_todo.py
│       ├── test_list_todos.py
│       ├── test_update_todo.py
│       ├── test_delete_todo.py
│       └── test_search_todos.py
└── integration/         # EXISTING: End-to-end tests
```

**Structure Decision**: Single project (Option 1) with new `src/mcp_server/` module for the FastMCP Database Server. This module is separate from the existing AI Agent Orchestrator but lives in the same repository since both features are part of the same Todo management system. The MCP server will be executed as a standalone process using `uvx fastmcp run src/mcp_server/server.py`.

## Phase 0: Research & Technology Validation

### Research Tasks

1. **FastMCP Framework Best Practices**
   - Fetch MCP docs for FastMCP SDK (tool registration, server lifecycle)
   - Understand MCP Content object structure
   - Validate tool execution patterns

2. **psycopg2 + SQLModel Integration**
   - ✅ psycopg2 connection patterns (COMPLETED - docs fetched)
   - ✅ Thread-safe connection pooling (COMPLETED - `ThreadedConnectionPool`)
   - ✅ SQLModel engine creation (COMPLETED - `create_engine` with PostgreSQL URL)
   - Validate psycopg2 URL format with SQLModel

3. **Database Connection Management**
   - Connection pool configuration (min=2, max=10)
   - Transaction handling (commit/rollback patterns)
   - Session lifecycle with SQLModel
   - Error handling for connection failures

### Research Output: `research.md`

Document findings on:
- FastMCP tool registration patterns
- psycopg2 `ThreadedConnectionPool` configuration
- SQLModel + psycopg2 integration (engine creation, session management)
- MCP Content object structure for returning results
- Error handling patterns for database failures

## Phase 1: Design & Contracts

### Data Model Design (`data-model.md`)

**Entity**: Todo

```python
# Preliminary schema (to be refined in Phase 1)
class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)  # Auto-incrementing
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: str = Field(default="active")  # "active" | "completed" | "archived"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### MCP Tool Contracts (`contracts/mcp-tools.json`)

Define JSON schemas for:
1. `create_todo` - Input: title (required), description (optional) → Output: Todo object
2. `list_todos` - Input: None → Output: List[Todo]
3. `update_todo` - Input: id, fields to update → Output: Updated Todo
4. `delete_todo` - Input: id → Output: Success confirmation
5. `search_todos` - Input: keyword → Output: List[Todo] (active only)

### Database Configuration (`quickstart.md`)

**psycopg2 Connection Setup**:
```python
# DATABASE_URL format for psycopg2 (NOT asyncpg)
DATABASE_URL = "postgresql://user:password@host:port/database"

# SQLModel engine with psycopg2
from sqlmodel import create_engine
from psycopg2 import pool

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=2,         # Minimum connections
    max_overflow=8,      # Maximum additional connections (total max = 10)
)

# Thread-safe connection pool (alternative approach)
connection_pool = pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=10,
    dsn=DATABASE_URL
)
```

**Key Design Decisions**:
- Use SQLModel's `create_engine` for ORM operations (leverages psycopg2 underneath)
- Connection pooling managed by SQLAlchemy (SQLModel's underlying engine)
- Synchronous database operations (psycopg2 is synchronous, not async)
- Session-per-tool-invocation pattern

## Key Technical Notes

### psycopg2 vs asyncpg

**Change Rationale**: Using `psycopg2` instead of `asyncpg` for the following reasons:
1. **Simplicity**: Synchronous operations are sufficient for MCP tool execution
2. **SQLModel Compatibility**: Better documented integration patterns
3. **Thread Safety**: `ThreadedConnectionPool` provides safe concurrent access
4. **Maturity**: psycopg2 is stable and widely used

**Trade-offs**:
- ❌ No async/await support (not needed for MCP tools)
- ✅ Simpler error handling
- ✅ Thread-safe connection pooling
- ✅ Well-established patterns with SQLModel

### Database URL Format

**IMPORTANT**: psycopg2 uses a different URL format than asyncpg:

```bash
# ❌ WRONG (asyncpg format)
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# ✅ CORRECT (psycopg2 format)
DATABASE_URL=postgresql://user:pass@host/db
# OR with explicit driver
DATABASE_URL=postgresql+psycopg2://user:pass@host/db
```

### Connection Pooling Strategy

**Approach**: Use SQLAlchemy's built-in connection pooling (via SQLModel)

```python
from sqlmodel import create_engine, Session

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Verify connection before use
    pool_size=2,              # Minimum connections
    max_overflow=8,           # Max additional connections
    pool_recycle=3600,        # Recycle connections after 1 hour
)

# Session-per-tool pattern
def create_todo_tool(title: str, description: str = None):
    with Session(engine) as session:
        todo = Todo(title=title, description=description)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo
```

## Next Steps

After plan approval:
1. ✅ Run `/sp.tasks` to generate implementation task breakdown
2. Execute Phase 0 research (fetch FastMCP docs)
3. Create data model and contracts (Phase 1)
4. Implement MCP tools (Phase 2 - via `/sp.implement`)
5. Write tests and validate against acceptance criteria
