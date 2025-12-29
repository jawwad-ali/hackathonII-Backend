# Implementation Plan: FastMCP Database Server for Todo Management

**Branch**: `002-fastmcp-database-server` | **Date**: 2025-12-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-fastmcp-database-server/spec.md`

**Note**: This plan follows the `/sp.plan` workflow. Implementation executes through `/sp.tasks` and `/sp.implement`.

## Summary

Build a FastMCP-based Model Context Protocol (MCP) server that provides standardized database tools for Todo CRUD operations. The server encapsulates all PostgreSQL persistence logic using SQLModel (async ORM) and exposes five MCP-compliant tools: `create_todo`, `list_todos`, `update_todo`, `delete_todo`, and `search_todos`. This server acts as the data layer for the AI Agent Orchestrator, enabling conversational todo management through tool invocation.

**Technical Approach**: Use FastMCP framework for tool registration, SQLModel for type-safe async database operations with Neon PostgreSQL (via `postgresql+asyncpg://` with SSL), and Pydantic models for strict input validation. All tools return MCP-compliant Content objects with descriptive text/JSON for agent interpretation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP (2.0+), SQLModel (0.0.14+), asyncpg (0.29+), python-dotenv (1.0+), Pydantic (2.0+)
**Storage**: Neon PostgreSQL (serverless, async via asyncpg driver with SSL requirement)
**Testing**: pytest with pytest-asyncio for async test support
**Target Platform**: Linux/Windows server environment (MCP server process)
**Project Type**: Single project (MCP server standalone process)
**Performance Goals**: <500ms response time for all tool invocations under normal load, handle 100 concurrent tool calls
**Constraints**:
- Neon PostgreSQL requires `sslmode=require` in connection string
- All database operations must be async (no blocking I/O)
- Tools must return MCP Content objects (not raw Python types)
- Connection pooling required for serverless Neon architecture
- Title max 200 chars, description max 2000 chars (validated before DB)

**Scale/Scope**:
- 5 MCP tools (create, list, update, delete, search)
- 1 SQLModel entity (Todo)
- Single async database engine with connection pool
- Support for multiple concurrent AI agent connections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Environment-First Rule
- **Status**: PASS
- **Verification**: All commands will use `.venv` activation prefix (Windows: `.venv\Scripts\activate`, Unix: `source .venv/bin/activate`)
- **Enforcement**: All installation and execution commands documented in plan and quickstart will include environment verification step

### ✅ Source of Truth Protocol (MCP Documentation)
- **Status**: PASS - Phase 0 research required
- **Libraries requiring MCP context-7 fetch**:
  1. FastMCP (Official Python SDK) - `/modelcontextprotocol/python-sdk` or equivalent
  2. SQLModel - `/tiangolo/sqlmodel`
  3. PostgreSQL async drivers - asyncpg documentation
  4. Pydantic (validation patterns) - `/pydantic/pydantic`
- **Action**: Phase 0 will resolve library IDs and fetch latest docs for:
  - FastMCP 2.0 tool registration and lifespan decorator patterns
  - SQLModel async session management and engine configuration
  - asyncpg connection string format and SSL configuration
  - Pydantic model validation for MCP tool inputs

### ✅ uv-Exclusive Package Management
- **Status**: PASS
- **Verification**: All dependency management uses `uv pip install`, `uv run`, and `uv pip compile`
- **Enforcement**: pyproject.toml will declare all dependencies, locked via requirements.txt

### ⚠️ Pre-Flight Skills Requirement
- **Status**: IN PROGRESS
- **Completed**: `/sp.specify` (spec.md created), `/sp.plan` (this file, in progress)
- **Pending**: `/sp.tasks` (after Phase 1 completion), `/sp.implement` (execution phase)

### ✅ Model & Connectivity Architecture
- **Status**: N/A for this feature
- **Rationale**: This is the MCP database server layer. It does NOT interact with LLM models. The AI Agent Orchestrator (separate component) handles AsyncOpenAI + Gemini integration. This server only provides data tools.

### ⚠️ Test-First Development
- **Status**: PLANNED
- **Testing Strategy**:
  - Unit tests for SQLModel Todo model (CRUD operations)
  - Integration tests for each MCP tool (tool invocation → database → response)
  - Contract tests for MCP Content object structure
  - End-to-end test with test database (create → list → update → delete → search flow)
- **Coverage Target**: >80% for business logic (tool functions, database operations)

### Constitution Violations: NONE

No complexity justifications required. This is a straightforward MCP server with 5 tools and 1 entity model.

## Project Structure

### Documentation (this feature)

```text
specs/002-fastmcp-database-server/
├── plan.md              # This file (/sp.plan output)
├── research.md          # Phase 0: MCP docs, SQLModel async patterns, Neon config
├── data-model.md        # Phase 1: Todo entity schema with validation rules
├── quickstart.md        # Phase 1: Setup, environment, running MCP server
├── contracts/           # Phase 1: MCP tool JSON schemas (5 tools)
│   ├── create_todo.json
│   ├── list_todos.json
│   ├── update_todo.json
│   ├── delete_todo.json
│   └── search_todos.json
└── tasks.md             # Phase 2: /sp.tasks output (NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── mcp_server/                  # FastMCP database server (NEW)
│   ├── __init__.py
│   ├── server.py                # FastMCP server definition, lifespan, tool registration
│   ├── models.py                # SQLModel Todo entity
│   ├── database.py              # Async engine, session factory, connection pool
│   ├── tools/                   # MCP tool implementations
│   │   ├── __init__.py
│   │   ├── create_todo.py       # create_todo tool
│   │   ├── list_todos.py        # list_todos tool
│   │   ├── update_todo.py       # update_todo tool
│   │   ├── delete_todo.py       # delete_todo tool
│   │   └── search_todos.py      # search_todos tool
│   └── schemas.py               # Pydantic input validation models
│
├── agents/                      # Existing AI agent orchestrator (unchanged)
├── api/                         # Existing FastAPI routes (unchanged)
└── config.py                    # Shared config (may add MCP server settings)

tests/
├── mcp_server/                  # NEW: Tests for MCP server
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures (test DB, async session)
│   ├── test_models.py           # SQLModel Todo CRUD tests
│   ├── test_tools.py            # MCP tool integration tests
│   └── test_database.py         # Database connection and session tests
│
└── [existing test directories]

.env                              # Add DATABASE_URL for Neon PostgreSQL
.env.example                      # Template with dummy Neon connection string
```

**Structure Decision**: Single project structure extended with new `src/mcp_server/` directory. This MCP server is a standalone process (separate from FastAPI orchestrator) but shares the same repository for monorepo convenience. The MCP server runs independently and is invoked by the AI Agent Orchestrator via MCP client protocol.

**Integration Note**: The existing AI Agent Orchestrator (`src/agents/`, `src/api/`) will connect to this MCP server as an MCP client. That integration is NOT part of this feature (002) - this spec focuses solely on building the MCP database server.

## Complexity Tracking

> **No violations - this section intentionally left empty**

---

## Phase 0: Research & Documentation Gathering

**Objective**: Resolve all "NEEDS CLARIFICATION" from Technical Context by fetching current library documentation via MCP context-7 server.

### Research Tasks

1. **FastMCP Framework Patterns**
   - **Unknown**: Latest FastMCP 2.0 tool registration syntax, lifespan decorator usage, Content object structure
   - **Action**:
     - Resolve library ID: `mcp__context7__resolve-library-id` → FastMCP SDK
     - Fetch docs: `mcp__context7__get-library-docs(mode='code', topic='tool registration')`
     - Fetch docs: `mcp__context7__get-library-docs(mode='code', topic='lifespan')`
   - **Document in research.md**:
     - Decision: How to register async tools with FastMCP
     - Rationale: Ensure compatibility with MCP protocol specification
     - Alternatives: Manual MCP protocol implementation (rejected - FastMCP abstracts complexity)

2. **SQLModel Async Session Management**
   - **Unknown**: Best practices for async engine creation, session lifecycle, connection pooling for Neon serverless
   - **Action**:
     - Resolve library ID: `mcp__context7__resolve-library-id` → SQLModel
     - Fetch docs: `mcp__context7__get-library-docs(mode='code', topic='async session')`
     - Fetch docs: `mcp__context7__get-library-docs(mode='code', topic='database engine')`
   - **Document in research.md**:
     - Decision: Use `create_async_engine` with connection pool settings
     - Rationale: Neon serverless requires efficient connection pooling
     - Alternatives: Synchronous SQLModel (rejected - blocks event loop)

3. **Neon PostgreSQL Connection Configuration**
   - **Unknown**: Exact asyncpg connection string format with SSL, pool size recommendations
   - **Action**:
     - Fetch docs: `mcp__context7__get-library-docs` for asyncpg (if available)
     - OR WebSearch: "Neon PostgreSQL asyncpg connection string sslmode 2025"
   - **Document in research.md**:
     - Decision: `postgresql+asyncpg://user:pass@host/db?sslmode=require`
     - Rationale: Neon enforces SSL connections
     - Alternatives: psycopg3 (rejected - asyncpg has better async performance)

4. **Pydantic Validation for MCP Tools**
   - **Unknown**: How to structure Pydantic models for MCP tool input validation
   - **Action**:
     - Resolve library ID: `mcp__context7__resolve-library-id` → Pydantic
     - Fetch docs: `mcp__context7__get-library-docs(mode='code', topic='validation')`
   - **Document in research.md**:
     - Decision: Create Pydantic models for each tool's input schema
     - Rationale: Type safety and validation before database operations
     - Alternatives: Manual validation (rejected - error-prone, less maintainable)

5. **MCP Content Object Structure**
   - **Unknown**: Required format for MCP tool responses (Content object schema)
   - **Action**:
     - Fetch docs: `mcp__context7__get-library-docs(mode='info', topic='content objects')` from FastMCP
   - **Document in research.md**:
     - Decision: Return `Content` objects with `type`, `text`, and optional `data` fields
     - Rationale: MCP protocol compliance for agent interpretation
     - Alternatives: Raw JSON (rejected - not MCP-compliant)

### Research Output: research.md

**Deliverable**: `specs/002-fastmcp-database-server/research.md` with:
- All library IDs resolved
- Documentation references with version numbers
- Decisions for async patterns, connection config, validation, MCP compliance
- Code snippets from official docs (FastMCP tool example, SQLModel async session example)

**Success Criteria**: No "NEEDS CLARIFICATION" remains; all technical choices documented with rationale.

---

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete, all MCP documentation fetched

### 1.1 Data Model Design

**Output**: `specs/002-fastmcp-database-server/data-model.md`

**Content**:
- **Todo Entity**:
  - **Fields**:
    - `id`: Integer (auto-increment, PostgreSQL SERIAL, primary key)
    - `title`: String (max 200 chars, required, indexed for search)
    - `description`: String (max 2000 chars, optional, indexed for search)
    - `status`: Enum (values: "active", "completed", "archived"; default: "active")
    - `created_at`: DateTime (auto-generated, timezone-aware)
    - `updated_at`: DateTime (auto-updated on modification, timezone-aware)
  - **Validation Rules**:
    - Title: Non-empty, max 200 chars (validated by Pydantic before DB)
    - Description: Optional, max 2000 chars if provided
    - Status: Must be one of enum values (enforced by SQLModel)
  - **State Transitions**:
    - `active` → `completed` (via update_todo, soft delete)
    - `active` → `archived` (via update_todo, long-term storage)
    - `completed` → `active` (via update_todo, reactivation)
    - Any state → DELETED (via delete_todo, hard delete - permanent removal)
  - **Indexes**:
    - Primary: `id` (auto)
    - Search: GIN index on `title` and `description` (PostgreSQL full-text search)
    - Filter: Index on `status` for efficient active/completed queries

### 1.2 API Contracts (MCP Tools)

**Output**: `specs/002-fastmcp-database-server/contracts/` directory with 5 JSON schemas

#### contracts/create_todo.json
```json
{
  "tool_name": "create_todo",
  "description": "Creates a new todo item in the database",
  "input_schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Todo title (required, max 200 chars)",
        "maxLength": 200
      },
      "description": {
        "type": "string",
        "description": "Optional todo description (max 2000 chars)",
        "maxLength": 2000
      }
    },
    "required": ["title"]
  },
  "output_schema": {
    "type": "object",
    "description": "MCP Content object with created todo",
    "properties": {
      "type": { "const": "text" },
      "text": { "type": "string", "description": "Human-readable success message" },
      "data": {
        "type": "object",
        "description": "Created todo object",
        "properties": {
          "id": { "type": "integer" },
          "title": { "type": "string" },
          "description": { "type": "string" },
          "status": { "enum": ["active"] },
          "created_at": { "type": "string", "format": "date-time" },
          "updated_at": { "type": "string", "format": "date-time" }
        }
      }
    }
  }
}
```

#### contracts/list_todos.json
```json
{
  "tool_name": "list_todos",
  "description": "Retrieves all active todos from the database",
  "input_schema": {
    "type": "object",
    "properties": {},
    "description": "No input parameters required"
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "type": { "const": "text" },
      "text": { "type": "string", "description": "Summary of results (e.g., 'Found 5 active todos')" },
      "data": {
        "type": "array",
        "description": "List of active todo objects",
        "items": {
          "type": "object",
          "properties": {
            "id": { "type": "integer" },
            "title": { "type": "string" },
            "description": { "type": "string" },
            "status": { "enum": ["active"] },
            "created_at": { "type": "string", "format": "date-time" },
            "updated_at": { "type": "string", "format": "date-time" }
          }
        }
      }
    }
  }
}
```

#### contracts/update_todo.json
```json
{
  "tool_name": "update_todo",
  "description": "Updates an existing todo by ID",
  "input_schema": {
    "type": "object",
    "properties": {
      "id": {
        "type": "integer",
        "description": "Todo ID to update"
      },
      "title": {
        "type": "string",
        "description": "New title (optional, max 200 chars)",
        "maxLength": 200
      },
      "description": {
        "type": "string",
        "description": "New description (optional, max 2000 chars)",
        "maxLength": 2000
      },
      "status": {
        "enum": ["active", "completed", "archived"],
        "description": "New status (optional)"
      }
    },
    "required": ["id"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "type": { "const": "text" },
      "text": { "type": "string", "description": "Update confirmation message" },
      "data": {
        "type": "object",
        "description": "Updated todo object",
        "properties": {
          "id": { "type": "integer" },
          "title": { "type": "string" },
          "description": { "type": "string" },
          "status": { "enum": ["active", "completed", "archived"] },
          "created_at": { "type": "string", "format": "date-time" },
          "updated_at": { "type": "string", "format": "date-time" }
        }
      }
    }
  }
}
```

#### contracts/delete_todo.json
```json
{
  "tool_name": "delete_todo",
  "description": "Permanently deletes a todo by ID (hard delete)",
  "input_schema": {
    "type": "object",
    "properties": {
      "id": {
        "type": "integer",
        "description": "Todo ID to delete"
      }
    },
    "required": ["id"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "type": { "const": "text" },
      "text": { "type": "string", "description": "Deletion confirmation message" },
      "data": {
        "type": "object",
        "description": "Deleted todo ID confirmation",
        "properties": {
          "id": { "type": "integer" },
          "deleted": { "const": true }
        }
      }
    }
  }
}
```

#### contracts/search_todos.json
```json
{
  "tool_name": "search_todos",
  "description": "Searches active todos by keyword in title or description",
  "input_schema": {
    "type": "object",
    "properties": {
      "keyword": {
        "type": "string",
        "description": "Search keyword (case-insensitive, searches title and description)"
      }
    },
    "required": ["keyword"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "type": { "const": "text" },
      "text": { "type": "string", "description": "Search results summary (e.g., 'Found 3 todos matching keyword')" },
      "data": {
        "type": "array",
        "description": "List of matching active todo objects",
        "items": {
          "type": "object",
          "properties": {
            "id": { "type": "integer" },
            "title": { "type": "string" },
            "description": { "type": "string" },
            "status": { "enum": ["active"] },
            "created_at": { "type": "string", "format": "date-time" },
            "updated_at": { "type": "string", "format": "date-time" }
          }
        }
      }
    }
  }
}
```

### 1.3 Quickstart Guide

**Output**: `specs/002-fastmcp-database-server/quickstart.md`

**Content**:
1. **Environment Setup**:
   - Activate `.venv` (Windows/Unix commands)
   - Install dependencies: `uv pip install fastmcp sqlmodel asyncpg python-dotenv`

2. **Database Configuration**:
   - Create Neon PostgreSQL database (link to Neon console)
   - Copy connection string with `?sslmode=require`
   - Add to `.env`: `DATABASE_URL=postgresql+asyncpg://user:pass@host/db?sslmode=require`

3. **Running MCP Server**:
   - Command: `uv run python -m src.mcp_server.server`
   - Expected output: "FastMCP server listening on stdio"
   - Lifespan log: "Database engine initialized, tables created"

4. **Testing with MCP Inspector** (optional):
   - Install MCP Inspector: `npm install -g @modelcontextprotocol/inspector`
   - Run: `mcp-inspector python -m src.mcp_server.server`
   - Test tool invocations in browser UI

5. **Integration with Agent Orchestrator** (future step):
   - Configure MCP client in agent orchestrator
   - Reference this server process in MCP client config
   - Invoke tools via MCP protocol

### 1.4 Agent Context Update

**Action**: Run PowerShell script to update Claude Code agent context

```powershell
.specify\scripts\powershell\update-agent-context.ps1 -AgentType claude
```

**Expected Changes**: Add to `.claude/agent-context.md` (or equivalent):
- FastMCP 2.0 framework (tool registration, lifespan)
- SQLModel async patterns (for future reference in other features)
- Neon PostgreSQL async connection patterns
- MCP Content object structure

**Manual Verification**: Ensure script preserves existing content between markers.

---

## Phase 2: Task Generation (Deferred to /sp.tasks)

**NOT executed by /sp.plan.** This phase is handled by the `/sp.tasks` command, which will:
1. Read this plan.md, research.md, data-model.md, and contracts/
2. Generate dependency-ordered implementation tasks in `tasks.md`
3. Include test tasks for each component
4. Specify acceptance criteria for each task

**Expected Task Categories** (preview for /sp.tasks):
- Database setup (SQLModel model, async engine, session factory)
- MCP tool implementation (5 tools)
- Input validation (Pydantic schemas)
- Integration tests (each tool + database)
- End-to-end test (full CRUD flow)
- Documentation (inline docstrings, README updates)

---

## Validation Checklist

**Pre-Phase 0**:
- [x] Technical Context filled (no NEEDS CLARIFICATION remaining in plan)
- [x] Constitution Check complete (all gates addressed)
- [x] Project Structure defined (source tree + docs tree)

**Post-Phase 0** (research.md):
- [ ] All MCP library IDs resolved
- [ ] FastMCP, SQLModel, asyncpg, Pydantic docs fetched
- [ ] All technical decisions documented with rationale

**Post-Phase 1** (design artifacts):
- [ ] data-model.md created with Todo entity schema
- [ ] contracts/ directory with 5 JSON tool schemas
- [ ] quickstart.md created with setup instructions
- [ ] Agent context updated via PowerShell script

**Ready for /sp.tasks**:
- [ ] All Phase 1 deliverables complete
- [ ] No unresolved technical questions
- [ ] Implementation approach clear from plan + research + contracts

---

## Next Steps

1. **Execute Phase 0**: Run research tasks to fetch MCP documentation (see Phase 0 section)
2. **Execute Phase 1**: Generate data-model.md, contracts/, quickstart.md (see Phase 1 section)
3. **Update Agent Context**: Run PowerShell script (see Phase 1.4)
4. **Signal Completion**: Report to user that plan.md is ready for /sp.tasks

**Command to continue**: `/sp.tasks` (after Phase 0 and Phase 1 complete)
