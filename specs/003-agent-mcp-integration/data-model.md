# Data Model: Agent-MCP Integration

**Feature**: 003-agent-mcp-integration
**Date**: 2025-12-31
**Status**: Complete

## Overview

This document defines the data structures and entities used in the Agent-MCP integration. Note that most entities are **runtime state** (not persisted to database) and exist only during application lifecycle or request scope.

---

## Entity Catalog

### 1. MCP Connection

**Type**: Runtime state (global, application-scoped)
**Persistence**: None (in-memory only)
**Lifecycle**: Created on FastAPI startup, destroyed on shutdown

#### Description
Represents the active connection between the FastAPI orchestrator and the FastMCP Database Server. Manages subprocess lifecycle and connection state tracking.

#### Attributes

| Attribute             | Type                          | Required | Description                                                |
|-----------------------|-------------------------------|----------|------------------------------------------------------------|
| `transport_type`      | `Literal["stdio", "sse"]`     | Yes      | Transport protocol (stdio for development, sse for prod)   |
| `server_name`         | `str`                         | Yes      | MCP server name ("TodoDatabaseServer")                     |
| `process_handle`      | `subprocess.Popen | None`     | No       | Subprocess handle (only for stdio transport)               |
| `connection_state`    | `Literal["connected", "disconnected", "degraded"]` | Yes | Current connection state |
| `last_health_check`   | `datetime`                    | Yes      | Timestamp of last successful health check                  |
| `discovered_tools`    | `list[ToolDefinition]`        | Yes      | Tools registered from MCP server (see Tool Registry)       |
| `initialization_time` | `float`                       | Yes      | Time taken to initialize connection (seconds)              |

#### State Transitions

```
[STARTUP] → [CONNECTING] → [CONNECTED] ──────────────────────┐
                                │                             │
                                │ (5 failures)                │ (recovery)
                                ▼                             │
                            [DEGRADED] ──────────────────────┘
                                │
                                │ (shutdown)
                                ▼
                          [DISCONNECTED]
```

#### Storage Location
- **FastAPI**: `app.state.mcp_server` (MCPServerStdio instance)
- **Circuit Breaker**: `_mcp_circuit_breaker` in `src/resilience/circuit_breaker.py`

#### Example Representation
```python
# Stored in FastAPI app.state
app.state.mcp_server = MCPServerStdio(
    name="TodoDatabaseServer",
    params={
        "command": "uvx",
        "args": ["fastmcp", "run", "src/mcp_server/server.py"]
    }
)

# Connection metadata (conceptual)
{
    "transport_type": "stdio",
    "server_name": "TodoDatabaseServer",
    "process_handle": <Popen object>,
    "connection_state": "connected",
    "last_health_check": "2025-12-31T10:30:00Z",
    "discovered_tools": [...],  # See Tool Registry
    "initialization_time": 1.23
}
```

---

### 2. Tool Registry

**Type**: Runtime state (global, application-scoped)
**Persistence**: None (in-memory only)
**Lifecycle**: Populated on MCP connection initialization

#### Description
Collection of tools discovered from the FastMCP Database Server. Each tool definition includes name, description, and parameter schema for LLM function calling.

#### Tool Definition Schema

| Attribute          | Type                  | Required | Description                                                |
|--------------------|-----------------------|----------|------------------------------------------------------------|
| `name`             | `str`                 | Yes      | Tool name (e.g., "create_todo", "list_todos")              |
| `description`      | `str`                 | Yes      | Tool description for LLM (from function docstring)         |
| `input_schema`     | `dict`                | Yes      | JSON Schema for input parameters                           |
| `tags`             | `set[str]`            | No       | Tool categorization tags (if any)                          |
| `metadata`         | `dict`                | No       | Custom metadata (version, author, etc.)                    |

#### Expected Tools (from FastMCP Server)

1. **create_todo**
   - Description: "Creates a new todo item with title, optional description, priority, tags, and due date"
   - Parameters: `title` (str, required), `description` (str, optional), `priority` (int, optional), `tags` (list[str], optional), `due_date` (str, optional)

2. **list_todos**
   - Description: "Lists todos filtered by status, priority, tags, or due date"
   - Parameters: `status` (str, optional), `priority` (int, optional), `tags` (list[str], optional), `due_date_before` (str, optional), `due_date_after` (str, optional)

3. **update_todo**
   - Description: "Updates an existing todo's fields by ID"
   - Parameters: `todo_id` (int, required), `title` (str, optional), `description` (str, optional), `status` (str, optional), `priority` (int, optional), `tags` (list[str], optional), `due_date` (str, optional)

4. **search_todos**
   - Description: "Searches todos by keyword in title or description"
   - Parameters: `query` (str, required), `status` (str, optional), `priority` (int, optional)

5. **delete_todo**
   - Description: "Deletes a todo by ID"
   - Parameters: `todo_id` (int, required)

#### Storage Location
- **Agent**: Inherited automatically via `Agent(mcp_servers=[server])`
- **SDK Internal**: Managed by OpenAI Agents SDK (no manual storage required)

#### Example Representation
```json
{
  "tools": [
    {
      "name": "create_todo",
      "description": "Creates a new todo item with title, optional description, priority, tags, and due date",
      "input_schema": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "description": {"type": "string"},
          "priority": {"type": "integer", "minimum": 1, "maximum": 5},
          "tags": {"type": "array", "items": {"type": "string"}},
          "due_date": {"type": "string", "format": "date"}
        },
        "required": ["title"]
      },
      "tags": ["crud", "create"],
      "metadata": {"version": "1.0"}
    }
    // ... 4 more tools
  ]
}
```

---

### 3. Tool Call Context

**Type**: Request-scoped state
**Persistence**: Logged to structured logs (not stored in database)
**Lifecycle**: Created per tool invocation, destroyed after response

#### Description
Metadata attached to each MCP tool call for observability, debugging, and audit trails. Includes correlation IDs, timing information, and execution results.

#### Attributes

| Attribute            | Type                  | Required | Description                                                |
|----------------------|-----------------------|----------|------------------------------------------------------------|
| `request_id`         | `str`                 | Yes      | Request correlation ID (from middleware)                   |
| `thread_id`          | `str`                 | No       | Conversation thread ID (if applicable)                     |
| `tool_name`          | `str`                 | Yes      | Name of tool being called (e.g., "create_todo")            |
| `parameters`         | `dict`                | Yes      | Tool input parameters                                      |
| `execution_start`    | `datetime`            | Yes      | When tool execution started                                |
| `execution_duration` | `float`               | Yes      | Tool execution time in seconds                             |
| `result`             | `Any`                 | No       | Tool execution result (if successful)                      |
| `error`              | `str`                 | No       | Error message (if failed)                                  |
| `status`             | `Literal["success", "failure", "timeout"]` | Yes | Execution status |

#### Example Representation
```json
{
  "request_id": "req_abc123",
  "thread_id": "thread_xyz789",
  "tool_name": "create_todo",
  "parameters": {
    "title": "Buy groceries",
    "priority": 2,
    "tags": ["shopping", "errands"]
  },
  "execution_start": "2025-12-31T10:30:15Z",
  "execution_duration": 0.345,
  "result": {
    "id": 42,
    "title": "Buy groceries",
    "status": "active",
    "created_at": "2025-12-31T10:30:15Z"
  },
  "status": "success"
}
```

#### Logging Format
Tool call context is logged using structured JSON logging (`src/observability/logging.py`):

```python
logger.info(
    "MCP tool call completed",
    extra={
        "request_id": context.request_id,
        "tool_name": context.tool_name,
        "duration": context.execution_duration,
        "status": context.status
    }
)
```

---

### 4. Circuit Breaker State

**Type**: Runtime state (global, singleton per service)
**Persistence**: None (in-memory only)
**Lifecycle**: Initialized on application startup, persists until shutdown

#### Description
Tracks health status of external services (MCP server and Gemini API) to prevent cascading failures. Implements circuit breaker pattern with three states: CLOSED, OPEN, HALF-OPEN.

#### Attributes

| Attribute              | Type                              | Required | Description                                                |
|------------------------|-----------------------------------|----------|------------------------------------------------------------|
| `service_name`         | `Literal["mcp", "gemini"]`        | Yes      | Service being monitored                                    |
| `state`                | `Literal["CLOSED", "OPEN", "HALF-OPEN"]` | Yes | Current circuit breaker state |
| `failure_count`        | `int`                             | Yes      | Consecutive failures since last success                    |
| `failure_threshold`    | `int`                             | Yes      | Max failures before opening (3 for Gemini, 5 for MCP)      |
| `last_failure_time`    | `datetime | None`                 | No       | Timestamp of most recent failure                           |
| `recovery_timeout`     | `timedelta`                       | Yes      | Time to wait before attempting recovery (60s Gemini, 30s MCP) |
| `last_state_change`    | `datetime`                        | Yes      | When state last transitioned                               |

#### State Transitions

```
[CLOSED] ──────────────────────────────────────────────┐
   │                                                    │
   │ (failures >= threshold)                            │ (success)
   ▼                                                    │
[OPEN] ─────────────────────────┐                      │
   │                             │                      │
   │ (after recovery_timeout)    │ (failure)            │
   ▼                             │                      │
[HALF-OPEN] ────────────────────┴──────────────────────┘
   │
   │ (success)
   └───────────────────────────────────────────────────┘
```

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service failing, requests fail immediately (no retries)
- **HALF-OPEN**: Testing recovery, single request allowed

#### Configuration

**MCP Circuit Breaker** (src/resilience/circuit_breaker.py):
```python
_mcp_circuit_breaker = CircuitBreaker(
    name="mcp_server",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=timedelta(seconds=30)
    )
)
```

**Gemini Circuit Breaker** (src/config.py):
```python
_gemini_circuit_breaker = CircuitBreaker(
    name="gemini_api",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=timedelta(seconds=60)
    )
)
```

#### Example Representation
```json
{
  "service_name": "mcp",
  "state": "OPEN",
  "failure_count": 5,
  "failure_threshold": 5,
  "last_failure_time": "2025-12-31T10:30:00Z",
  "recovery_timeout": "PT30S",
  "last_state_change": "2025-12-31T10:30:00Z"
}
```

---

## Entity Relationships

```
┌─────────────────────────────┐
│   FastAPI Application       │
│   (app.state)               │
└────────────┬────────────────┘
             │
             │ 1:1 (global)
             ▼
┌─────────────────────────────┐
│   MCP Connection            │
│   - transport_type          │
│   - connection_state        │
│   - discovered_tools ────┐  │
└─────────────────────────────┘
                              │
                              │ 1:N
                              ▼
                  ┌─────────────────────────────┐
                  │   Tool Registry             │
                  │   - create_todo             │
                  │   - list_todos              │
                  │   - update_todo             │
                  │   - search_todos            │
                  │   - delete_todo             │
                  └─────────────────────────────┘
                              │
                              │ 1:N (per request)
                              ▼
                  ┌─────────────────────────────┐
                  │   Tool Call Context         │
                  │   - request_id              │
                  │   - tool_name               │
                  │   - parameters              │
                  │   - result                  │
                  └─────────────────────────────┘

┌─────────────────────────────┐
│   Circuit Breaker (Global)  │
│   - MCP Server              │
│   - Gemini API              │
└─────────────────────────────┘
             │
             │ monitors
             ▼
   MCP Connection health
```

---

## Validation Rules

### MCP Connection
- `transport_type` must be "stdio" or "sse"
- `connection_state` must be "connected", "disconnected", or "degraded"
- `process_handle` required if `transport_type == "stdio"`
- `initialization_time` must be >= 0

### Tool Registry
- Each tool must have unique `name`
- `input_schema` must be valid JSON Schema
- All tools from MCP server must be registered (no filtering)

### Tool Call Context
- `request_id` must be valid UUID or correlation ID
- `execution_duration` must be >= 0
- `result` and `error` are mutually exclusive (one or neither, not both)
- `status` must match: `success` → `result` present, `failure/timeout` → `error` present

### Circuit Breaker
- `failure_threshold` must be > 0
- `recovery_timeout` must be > 0 seconds
- `failure_count` must be >= 0
- `state` transitions must follow pattern (no skipping states)

---

## Migration Notes

**No database migrations required**. All entities are runtime state.

**Existing Database Schema** (unchanged):
- `Todo` table in PostgreSQL (managed by FastMCP server via SQLModel)
- No changes to database schema for Agent-MCP integration

---

**Data Model Status**: ✅ COMPLETE - All entities defined, ready for implementation
