# Research: FastMCP Database Server Technical Documentation

**Feature**: 002-fastmcp-database-server
**Date**: 2025-12-29
**Purpose**: Document MCP-fetched library patterns and technical decisions for FastMCP database server implementation

## Overview

This document consolidates research findings from the MCP context-7 server for all libraries required to build the FastMCP database server. All decisions are based on current library documentation fetched on 2025-12-29.

---

## 1. FastMCP Framework Patterns

### Library Information
- **Library ID**: `/websites/gofastmcp`
- **Source Reputation**: High
- **Code Snippets Available**: 1879
- **Benchmark Score**: 79.6

### 1.1 Tool Registration

**Decision**: Use `@mcp.tool` decorator for async tool registration

**Rationale**: FastMCP provides a Pythonic decorator-based API for registering tools. The `@mcp.tool` decorator automatically:
- Converts Python function signatures into MCP-compliant tool schemas
- Handles async/await patterns natively
- Generates JSON schemas from type hints
- Returns MCP Content objects

**Code Pattern**:
```python
from fastmcp import FastMCP

mcp = FastMCP(name="TodoDatabaseServer")

@mcp.tool
async def create_todo(title: str, description: str = None) -> dict:
    """Creates a new todo item in the database."""
    # Implementation here
    return {"id": 1, "title": title, "description": description}
```

**Alternatives Considered**:
- Manual MCP protocol implementation (rejected - FastMCP abstracts JSON-RPC complexity)
- Synchronous tools (rejected - would block event loop during database I/O)

### 1.2 Async Database Operations with FastMCP

**Decision**: Use async context managers with `Depends()` for database session injection

**Rationale**: FastMCP integrates seamlessly with async context managers, ensuring proper resource cleanup even when errors occur. The `Depends()` pattern (similar to FastAPI) provides dependency injection for database sessions.

**Code Pattern**:
```python
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from fastmcp.dependencies import Depends

mcp = FastMCP(name="TodoDatabaseServer")

@asynccontextmanager
async def get_database_session():
    """Provides an async database session with automatic cleanup."""
    async with AsyncSession(engine) as session:
        try:
            yield session
        finally:
            await session.close()

@mcp.tool
async def create_todo(
    title: str,
    description: str = None,
    session = Depends(get_database_session)
) -> dict:
    """Creates a new todo with automatic session management."""
    db_todo = Todo(title=title, description=description)
    session.add(db_todo)
    await session.commit()
    await session.refresh(db_todo)
    return db_todo.model_dump()
```

**Alternatives Considered**:
- Manual session management in each tool (rejected - error-prone, repetitive)
- Synchronous database operations (rejected - blocks event loop)

### 1.3 Server Execution

**Decision**: Use `await mcp.run_async()` for async server execution

**Rationale**: The MCP server runs as a standalone process using stdio transport by default. For async environments, `run_async()` is the recommended method.

**Code Pattern**:
```python
import asyncio
from fastmcp import FastMCP

mcp = FastMCP(name="TodoDatabaseServer")

# ... tool definitions ...

async def main():
    await mcp.run_async(transport="stdio")

if __name__ == "__main__":
    asyncio.run(main())
```

**Alternatives Considered**:
- Synchronous `mcp.run()` (rejected - not suitable for async database operations)
- HTTP transport (deferred - stdio is MCP standard for local server processes)

---

## 2. SQLModel Async Session Management

### Library Information
- **Library ID**: `/websites/sqlmodel_tiangolo`
- **Source Reputation**: High
- **Code Snippets Available**: 2464
- **Benchmark Score**: 78.2

### 2.1 Async Engine Creation

**Decision**: Use `create_async_engine()` from SQLAlchemy with asyncpg driver

**Rationale**: SQLModel is built on SQLAlchemy and supports async operations through SQLAlchemy's async engine. The asyncpg driver provides high-performance async PostgreSQL connectivity.

**Code Pattern**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Neon PostgreSQL connection string with SSL
DATABASE_URL = "postgresql+asyncpg://user:pass@host.neon.tech/db?sslmode=require"

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # SQL logging (disable in production)
    pool_size=5,  # Connection pool size for serverless
    max_overflow=10,  # Max overflow connections
    pool_pre_ping=True,  # Verify connections before use
)

# Async session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-load errors after commit
)
```

**Alternatives Considered**:
- Synchronous SQLModel (rejected - blocks event loop, poor performance)
- psycopg3 driver (rejected - asyncpg has better async performance benchmarks)

### 2.2 Session Lifecycle Management

**Decision**: Use async context manager pattern with `async with AsyncSession(engine)`

**Rationale**: Context managers ensure sessions are properly closed, even when exceptions occur. This is critical for connection pool management in serverless environments like Neon.

**Code Pattern**:
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session():
    """Dependency for FastMCP tools to get database session."""
    async with AsyncSession(engine) as session:
        try:
            yield session
        finally:
            await session.close()
```

**Integration with FastMCP**:
```python
from fastmcp.dependencies import Depends

@mcp.tool
async def list_todos(session = Depends(get_session)) -> list[dict]:
    """Lists all active todos."""
    result = await session.execute(
        select(Todo).where(Todo.status == "active")
    )
    todos = result.scalars().all()
    return [todo.model_dump() for todo in todos]
```

**Alternatives Considered**:
- Manual session creation/closing (rejected - error-prone, leaks connections on exceptions)
- Global session (rejected - not thread-safe, doesn't support concurrent requests)

### 2.3 Table Creation with Async Engine

**Decision**: Use `SQLModel.metadata.create_all()` with `run_sync()` during server startup

**Rationale**: Table creation is a synchronous metadata operation in SQLAlchemy. Use `run_sync()` to execute it within the async engine.

**Code Pattern**:
```python
async def create_db_and_tables():
    """Creates database tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

**Lifespan Integration** (for FastMCP startup):
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan():
    """Lifespan context for database initialization."""
    # Startup: create tables
    await create_db_and_tables()
    print("Database initialized, tables created")
    yield
    # Shutdown: cleanup if needed
    await engine.dispose()
    print("Database engine disposed")

mcp = FastMCP(name="TodoDatabaseServer", lifespan=lifespan)
```

**Alternatives Considered**:
- Alembic migrations (deferred - overkill for single-entity MVP, add later for schema versioning)
- Manual CREATE TABLE SQL (rejected - SQLModel auto-generates from Python models)

---

## 3. Neon PostgreSQL Connection Configuration

### Library Information
- **Library ID**: `/websites/magicstack_github_io_asyncpg_current`
- **Source Reputation**: High
- **Code Snippets Available**: 502
- **Benchmark Score**: 70.9

### 3.1 Connection String Format

**Decision**: Use `postgresql+asyncpg://` protocol with `sslmode=require` query parameter

**Rationale**: Neon enforces SSL connections for security. The asyncpg driver requires the `postgresql+asyncpg://` scheme, and Neon requires the `sslmode=require` parameter.

**Connection String Format**:
```
postgresql+asyncpg://username:password@hostname.neon.tech/database?sslmode=require
```

**Example**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require"
)
```

**Environment Variable** (`.env`):
```env
DATABASE_URL=postgresql+asyncpg://myuser:mypassword@ep-cool-sound-123456.us-east-2.aws.neon.tech/mydb?sslmode=require
```

**Alternatives Considered**:
- `sslmode=prefer` (rejected - Neon requires SSL, prefer is insecure fallback)
- `postgresql://` without asyncpg (rejected - defaults to psycopg, not async)

### 3.2 Connection Pooling for Serverless

**Decision**: Configure connection pool with moderate size (5-10 connections) for Neon serverless

**Rationale**: Neon is serverless and scales connections dynamically. Moderate pool sizes prevent connection exhaustion while enabling concurrency. `pool_pre_ping=True` ensures stale connections are detected.

**Configuration**:
```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,  # Base pool size
    max_overflow=10,  # Additional connections under load
    pool_pre_ping=True,  # Verify connection health before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)
```

**Rationale for Parameters**:
- `pool_size=5`: Sufficient for moderate MCP tool concurrency (5 simultaneous tool calls)
- `max_overflow=10`: Handle bursts up to 15 total connections
- `pool_pre_ping=True`: Critical for serverless (connections may be closed server-side)
- `pool_recycle=3600`: Prevent long-lived connection issues with Neon's autoscaling

**Alternatives Considered**:
- Large pool sizes (50+) (rejected - wastes resources in serverless, Neon charges per connection)
- No pooling (rejected - poor performance, each tool call creates new connection)

### 3.3 Connection Parameters

**Decision**: Use asyncpg connection parameters via SQLAlchemy engine

**Key Parameters**:
- `command_timeout`: Set per-query timeout (default: None, set to 30s for safety)
- `timeout`: Connection establishment timeout (default: 60s, adequate for Neon)
- `statement_cache_size`: Prepared statement cache (default: 100, reduces parse overhead)

**Configuration**:
```python
engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "command_timeout": 30,  # 30-second query timeout
        "timeout": 60,  # 60-second connection timeout
        "statement_cache_size": 100,  # Cache 100 prepared statements
    },
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
```

**Alternatives Considered**:
- No timeouts (rejected - risk of hung connections on network issues)
- Very short timeouts (<10s) (rejected - may interrupt legitimate long queries)

---

## 4. Pydantic Validation for MCP Tools

### Library Information
- **Library ID**: `/websites/pydantic_dev`
- **Source Reputation**: High
- **Code Snippets Available**: 2805
- **Benchmark Score**: 94.4

### 4.1 Input Validation Strategy

**Decision**: Use Pydantic BaseModel classes for tool input validation before database operations

**Rationale**: Pydantic provides:
- Type coercion (strings to ints, etc.)
- Field-level validation (length limits, regex patterns)
- Custom validators for business logic
- Clear error messages for MCP tool callers

**Code Pattern**:
```python
from pydantic import BaseModel, Field, field_validator

class CreateTodoInput(BaseModel):
    """Input schema for create_todo tool."""
    title: str = Field(..., min_length=1, max_length=200, description="Todo title")
    description: str | None = Field(None, max_length=2000, description="Optional description")

    @field_validator("title", mode="after")
    @classmethod
    def title_not_empty_after_strip(cls, value: str) -> str:
        """Ensure title is not empty after stripping whitespace."""
        if not value.strip():
            raise ValueError("Title cannot be empty or whitespace-only")
        return value.strip()

@mcp.tool
async def create_todo(
    input_data: CreateTodoInput,
    session = Depends(get_session)
) -> dict:
    """Creates a new todo with validated input."""
    db_todo = Todo(**input_data.model_dump())
    session.add(db_todo)
    await session.commit()
    await session.refresh(db_todo)
    return db_todo.model_dump()
```

**Alternatives Considered**:
- Manual validation (rejected - error-prone, inconsistent error messages)
- Validation at database layer only (rejected - leaks invalid data to DB, poor error feedback)

### 4.2 Field Validators for Business Rules

**Decision**: Use `@field_validator` for field-level validation and `@model_validator` for cross-field validation

**Examples**:

**Title Validation**:
```python
@field_validator("title", mode="after")
@classmethod
def validate_title(cls, value: str) -> str:
    """Validate title is not just whitespace."""
    if not value.strip():
        raise ValueError("Title cannot be empty or whitespace-only")
    return value.strip()
```

**Status Enum Validation** (in SQLModel):
```python
from enum import Enum

class TodoStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Todo(SQLModel, table=True):
    status: TodoStatus = Field(default=TodoStatus.ACTIVE)
```

**Cross-field Validation** (future enhancement):
```python
from pydantic import model_validator

class UpdateTodoInput(BaseModel):
    id: int
    title: str | None = None
    description: str | None = None
    status: TodoStatus | None = None

    @model_validator(mode="after")
    def at_least_one_field_provided(self):
        """Ensure at least one field is being updated."""
        if all(v is None for v in [self.title, self.description, self.status]):
            raise ValueError("At least one field (title, description, status) must be provided for update")
        return self
```

**Alternatives Considered**:
- No validation (rejected - allows garbage data, poor UX)
- Database constraints only (rejected - less descriptive errors, harder to debug)

---

## 5. MCP Content Object Structure

### Library Information
- **Library ID**: `/websites/gofastmcp`
- **Source Reputation**: High

### 5.1 MCP Tool Response Format

**Decision**: Return structured dictionaries from tools; FastMCP automatically wraps them in MCP Content objects

**Rationale**: FastMCP automatically converts Python return values to MCP-compliant Content objects. Tools should return:
- Dictionaries for structured data
- Lists for collections
- Strings for simple messages

FastMCP handles the MCP protocol serialization.

**Code Pattern**:
```python
@mcp.tool
async def create_todo(title: str, description: str = None) -> dict:
    """Creates a new todo."""
    # ... database operations ...
    return {
        "id": db_todo.id,
        "title": db_todo.title,
        "description": db_todo.description,
        "status": db_todo.status,
        "created_at": db_todo.created_at.isoformat(),
        "updated_at": db_todo.updated_at.isoformat(),
    }

@mcp.tool
async def list_todos() -> list[dict]:
    """Lists all active todos."""
    # ... database query ...
    return [todo.model_dump() for todo in todos]
```

**MCP Wire Format** (automatic conversion by FastMCP):
```json
{
  "type": "text",
  "text": "Created todo successfully",
  "data": {
    "id": 1,
    "title": "Buy groceries",
    "description": "Milk, eggs, bread",
    "status": "active",
    "created_at": "2025-12-29T12:00:00Z",
    "updated_at": "2025-12-29T12:00:00Z"
  }
}
```

**Alternatives Considered**:
- Manual Content object creation (rejected - FastMCP handles this automatically)
- Raw JSON strings (rejected - FastMCP requires structured Python types)

### 5.2 Error Handling in Tools

**Decision**: Raise Python exceptions; FastMCP converts them to MCP error responses

**Code Pattern**:
```python
@mcp.tool
async def update_todo(id: int, title: str = None) -> dict:
    """Updates an existing todo."""
    result = await session.execute(select(Todo).where(Todo.id == id))
    todo = result.scalar_one_or_none()

    if todo is None:
        raise ValueError(f"Todo with ID {id} not found")

    if title:
        todo.title = title
    todo.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(todo)
    return todo.model_dump()
```

**MCP Error Response** (automatic):
```json
{
  "error": {
    "code": "ValueError",
    "message": "Todo with ID 123 not found"
  }
}
```

**Alternatives Considered**:
- Return error dictionaries (rejected - not MCP-compliant, inconsistent with protocol)
- Silent failures (rejected - breaks MCP contract, poor debugging)

---

## 6. Integration Architecture

### 6.1 Database Initialization Flow

```
1. Server Startup (asyncio.run(main()))
   ↓
2. Lifespan Context Entered
   ↓
3. Create Async Engine (with connection pool)
   ↓
4. Create Tables (via run_sync)
   ↓
5. MCP Server Listening (stdio transport)
   ↓
6. Tool Invocation (via MCP client)
   ↓
7. Session Injection (via Depends)
   ↓
8. Database Operation (async query/commit)
   ↓
9. Session Cleanup (automatic via context manager)
   ↓
10. Return Result (FastMCP converts to Content)
```

### 6.2 Error Handling Strategy

**Levels**:
1. **Input Validation** (Pydantic) → ValueError with field-specific messages
2. **Database Errors** (asyncpg) → Caught and re-raised as descriptive errors
3. **Business Logic** (custom) → ValueError with human-readable messages
4. **MCP Protocol** (FastMCP) → Automatic error response formatting

**Example**:
```python
from sqlalchemy.exc import IntegrityError

@mcp.tool
async def create_todo(title: str, session = Depends(get_session)) -> dict:
    try:
        db_todo = Todo(title=title)
        session.add(db_todo)
        await session.commit()
        await session.refresh(db_todo)
        return db_todo.model_dump()
    except IntegrityError as e:
        raise ValueError(f"Database integrity error: {str(e)}")
```

---

## 7. Testing Strategy

### 7.1 Test Database Setup

**Decision**: Use in-memory SQLite for unit tests, Neon staging for integration tests

**Code Pattern** (pytest fixture):
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import SQLModel

@pytest.fixture
async def test_session():
    """Provides a test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    await engine.dispose()
```

**Alternatives Considered**:
- Mocking database (rejected - doesn't test real SQL behavior)
- Shared test database (rejected - tests interfere with each other)

---

## Summary of Key Decisions

| Component | Decision | Library ID | Version |
|-----------|----------|------------|---------|
| MCP Framework | FastMCP with `@mcp.tool` decorator | `/websites/gofastmcp` | Latest |
| ORM | SQLModel with async SQLAlchemy | `/websites/sqlmodel_tiangolo` | Latest |
| Database Driver | asyncpg | `/websites/magicstack_github_io_asyncpg_current` | Latest |
| Validation | Pydantic v2 BaseModel | `/websites/pydantic_dev` | 2.0+ |
| Connection String | `postgresql+asyncpg://...?sslmode=require` | N/A | N/A |
| Session Management | Async context manager with `Depends()` | N/A | N/A |
| Error Handling | Python exceptions → MCP errors (automatic) | N/A | N/A |

---

## Next Steps

✅ **Phase 0 Complete**: All library documentation fetched and decisions documented

**Phase 1 Deliverables**:
1. `data-model.md` - Todo entity schema
2. `contracts/` - 5 MCP tool JSON schemas
3. `quickstart.md` - Setup and running instructions

**Command to Continue**: Proceed to Phase 1 artifact generation
