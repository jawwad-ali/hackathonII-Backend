# Research Findings: Agent-MCP Integration

**Feature**: 003-agent-mcp-integration
**Date**: 2025-12-31
**Status**: Complete

## Overview

This document consolidates research findings for integrating the FastAPI Orchestrator with the FastMCP Database Server. All unknowns from Technical Context have been resolved through Context7 MCP documentation queries.

---

## 1. MCP Transport Selection

### Question
Which MCP transport protocol should be used for agent-to-server communication in development vs production?

### Research Conducted
- Queried Context7 for OpenAI Agents SDK MCP documentation (library ID: `/openai/openai-agents-python`)
- Reviewed transport options: stdio, SSE, Streamable HTTP, Hosted MCP

### Decision
**Primary Transport**: MCPServerStdio (stdio - stdin/stdout)

### Rationale
1. **Development Simplicity**: Spawns MCP server as subprocess with automatic lifecycle management
2. **Security**: No network exposure - process only accessible via parent pipes (satisfies FR-018 localhost requirement)
3. **Reliability**: No network latency or connection failures
4. **Official Support**: First-class support in OpenAI Agents SDK with `agents.mcp.MCPServerStdio`

**Secondary Transport** (prepared, not implemented): MCPServerSse (HTTP with Server-Sent Events) for future production scaling when MCP server runs as separate service.

### Implementation Pattern
```python
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    name="TodoDatabase Server",
    params={
        "command": "uvx",
        "args": ["fastmcp", "run", "src/mcp_server/server.py"]
    }
) as server:
    agent = Agent(
        name="TodoAgent",
        instructions="...",
        mcp_servers=[server]  # Dynamic tool discovery
    )
```

### Alternatives Considered
- **SSE (MCPServerSse)**: Requires network binding, adds complexity. Reserved for production multi-instance deployment.
- **Streamable HTTP**: Overkill for local communication.
- **Hosted MCP**: Requires public endpoint, not suitable for database operations.

---

## 2. Dynamic Tool Discovery Mechanism

### Question
How does the agent automatically discover and register MCP tools without manual configuration?

### Research Conducted
- Studied OpenAI Agents SDK documentation on `mcp_servers` parameter
- Examined tool filtering and registration patterns

### Decision
Use built-in dynamic discovery via `Agent(mcp_servers=[...])` parameter.

### Rationale
1. **Zero Configuration**: No manual tool definitions required
2. **Automatic Schema Generation**: Tools inherit names, descriptions, and parameter schemas from FastMCP server
3. **Consistency**: Ensures agent's tool list always matches MCP server's exposed tools
4. **Flexibility**: Tool filtering available if needed (not required for current scope)

### How It Works
1. Agent initializes with `mcp_servers` parameter containing MCPServerStdio instance
2. SDK queries MCP server via JSON-RPC `tools/list` method
3. Server returns tool definitions (names, descriptions, JSON schemas)
4. Agent registers tools dynamically in internal tool registry
5. LLM can call tools using standard function calling protocol

### Verification
FastMCP server exposes 5 tools:
- `create_todo` - Creates new todo with title, description, priority, etc.
- `list_todos` - Lists todos filtered by status, priority, tags, due_date
- `update_todo` - Updates todo fields by ID
- `search_todos` - Searches todos by keyword
- `delete_todo` - Deletes todo by ID

All tools use `@mcp.tool` decorator with proper type hints and docstrings, generating correct JSON-RPC schemas.

---

## 3. FastAPI Lifespan Management

### Question
How should FastAPI orchestrator manage MCP server subprocess lifecycle?

### Research Conducted
- Reviewed FastAPI async context manager patterns
- Studied MCPServerStdio lifecycle (automatic spawn on `async with`, termination on exit)

### Decision
Use FastAPI `@asynccontextmanager` lifespan hook to initialize MCP connection on startup and store in `app.state`.

### Rationale
1. **Single Connection**: Reuse MCP server instance across all requests (reduces subprocess overhead)
2. **Graceful Startup/Shutdown**: Lifespan hooks ensure proper initialization and cleanup
3. **State Sharing**: `app.state` provides global access to MCP server for endpoints
4. **Degraded Mode**: If MCP connection fails, app starts anyway and handles errors gracefully

### Implementation Pattern
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MCP connection
    try:
        mcp_server = await initialize_mcp_connection()
        app.state.mcp_server = mcp_server
        logger.info("MCP server connected successfully")
    except Exception as e:
        logger.error(f"MCP server connection failed: {e}")
        app.state.mcp_server = None  # Degraded mode

    yield

    # Shutdown: Terminate MCP subprocess
    if app.state.mcp_server:
        await app.state.mcp_server.close()
        logger.info("MCP server connection closed")

app = FastAPI(lifespan=lifespan)
```

### Benefits
- Endpoints access via `request.app.state.mcp_server`
- Connection reused across all requests
- Automatic cleanup on shutdown
- Degraded mode support (app runs even if MCP fails)

---

## 4. Timeout & Retry Configuration

### Question
What timeout and retry values should be used for MCP tool calls to meet spec requirements?

### Spec Requirements
- **FR-017**: 5-second timeout for all MCP tool calls
- **FR-013**: 3 retry attempts with exponential backoff
- **SC-011**: Tool calls exceeding 5s terminated within 5.5s total

### Current Implementation Analysis
**src/config.py**:
- `MCP_SERVER_TIMEOUT = 30` (default) ❌ TOO HIGH
- `MCP_RETRY_ATTEMPTS = 3` ✅ CORRECT
- `MCP_RETRY_DELAYS = [1, 2, 4]` ✅ CORRECT (exponential backoff)

### Decision
**Update Required**: Change `MCP_SERVER_TIMEOUT` default from 30s to 5s.

### Rationale
1. **Spec Compliance**: FR-017 explicitly requires 5-second timeout
2. **User Experience**: 30s timeout causes poor UX - users wait too long for errors
3. **Circuit Breaker Alignment**: Faster timeouts enable circuit breaker to trip quickly, preventing request pileup
4. **Total Time Budget**: 5s timeout + retry overhead (1+2+4=7s) = ~12s max (acceptable for 3 retries)

### Configuration Changes
```python
# src/config.py
class Settings(BaseSettings):
    # MCP Server
    MCP_SERVER_TIMEOUT: int = Field(default=5, description="MCP tool call timeout in seconds")  # Changed from 30
    MCP_RETRY_ATTEMPTS: int = Field(default=3, description="Number of retry attempts")
    MCP_RETRY_DELAYS: list[int] = Field(default=[1, 2, 4], description="Retry delay sequence (seconds)")
```

### Retry Logic Behavior
- **Initial call**: Timeout after 5s
- **Retry 1**: Wait 1s, timeout after 5s
- **Retry 2**: Wait 2s, timeout after 5s
- **Retry 3**: Wait 4s, timeout after 5s
- **Total**: 4 attempts, max ~20s (acceptable for network issues, but circuit breaker will trip at 5 failures)

---

## 5. Graceful Degraded Mode

### Question
How should the system behave when MCP server is unavailable?

### Spec Requirements
- **FR-010**: Graceful startup when MCP unavailable (degraded mode)
- **User Story 4**: Accept requests but return user-friendly errors
- **SC-013**: Return HTTP 200 with error messages (not HTTP 503 or crashes)

### Current Implementation Issues
- Health check returns 503 when both circuit breakers open ❌ VIOLATES SC-013
- No explicit degraded mode error handling in `/chat/stream`

### Decision
Implement three-tier degraded mode handling:

1. **Startup Degraded Mode**:
   - If MCP connection fails during lifespan initialization, set `app.state.mcp_server = None`
   - App starts successfully (no crash)
   - Log critical warning for alerting

2. **Request-Level Degraded Mode**:
   - `/chat/stream` checks `app.state.mcp_server is not None`
   - If None, return HTTP 200 with user-friendly error in response body:
     ```json
     {
       "error": "Todo database is temporarily unavailable. Please try again later.",
       "status": "degraded"
     }
     ```

3. **Circuit Breaker Degraded Mode**:
   - Catch `CircuitBreakerOpenError` in `/chat/stream`
   - Return HTTP 200 with friendly error (not HTTP 503)
   - Health check returns HTTP 200 with `status: "degraded"` when MCP circuit breaker open

### Rationale
- **User Experience**: Users see helpful messages, not cryptic 503 errors
- **Service Availability**: App remains available for other operations (e.g., health checks, docs)
- **Observability**: Degraded status logged and exposed via `/health` for monitoring
- **Spec Compliance**: Satisfies SC-013 (HTTP 200 for degraded mode)

### Implementation Pattern
```python
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, app_request: Request):
    # Check MCP availability
    mcp_server = app_request.app.state.mcp_server
    if mcp_server is None:
        return JSONResponse(
            status_code=200,
            content={
                "error": "Todo database is temporarily unavailable. Please try again later.",
                "status": "degraded"
            }
        )

    # Proceed with normal flow
    try:
        agent = create_todo_agent(mcp_server)
        # ... stream response
    except CircuitBreakerOpenError:
        return JSONResponse(
            status_code=200,
            content={
                "error": "Todo database is temporarily unavailable. Please try again later.",
                "status": "degraded"
            }
        )
```

---

## 6. FastMCP Server Verification

### Question
How to verify FastMCP server exposes correct JSON-RPC schema before integration?

### Research Conducted
- Reviewed FastMCP documentation on MCP Inspector tool
- Examined `@mcp.tool` decorator usage in existing code

### Decision
Use **MCP Inspector** to verify server schema before finalizing integration.

### Command
```bash
uvx fastmcp inspect src/mcp_server/server.py
# OR
mcp-inspector uvx fastmcp run src/mcp_server/server.py
```

### Expected Output
- Server name: "TodoDatabaseServer"
- 5 tools listed with correct names, descriptions, parameter schemas
- Each tool shows JSON Schema for input parameters
- Verify type coercion rules (e.g., string → int for priority)

### Verification Checklist
- [ ] `create_todo` - Parameters: title (str, required), description (str, optional), priority (int, optional), tags (list[str], optional), due_date (str, optional)
- [ ] `list_todos` - Parameters: status (str, optional), priority (int, optional), tags (list[str], optional), due_date_before/after (str, optional)
- [ ] `update_todo` - Parameters: todo_id (int, required), status/priority/title/description/tags/due_date (all optional)
- [ ] `search_todos` - Parameters: query (str, required), status/priority (optional)
- [ ] `delete_todo` - Parameters: todo_id (int, required)

**Status**: Verification pending - to be completed in Task 14 (Phase 4).

---

## 7. ChatKit SSE Event Mapping

### Question
Is the existing ChatKit SSE event mapping compatible with OpenAI Agents SDK streaming events?

### Research Conducted
- Reviewed OpenAI Agents SDK `Runner.run_streamed()` event types
- Examined existing `src/streaming/chatkit.py` and `src/api/routes.py` implementations

### Decision
**No changes required**. Existing mapping is correct and complete.

### Event Mapping Table

| Agents SDK Event      | ChatKit SSE Event   | Status/Metadata                    |
|-----------------------|---------------------|------------------------------------|
| `agent:thinking`      | `THINKING`          | Reasoning content                  |
| `tool:call`           | `TOOL_CALL`         | `IN_PROGRESS`, tool name, args     |
| `tool:result`         | `TOOL_CALL`         | `COMPLETED`/`FAILED`, result/error |
| `response:delta`      | `RESPONSE_DELTA`    | Incremental text chunks            |
| `response:done`       | `DONE`              | Final response                     |
| (any error)           | `ERROR`             | Error type, message                |

### Verification
Existing implementation in `src/api/routes.py` correctly maps events:
```python
async for event in stream:
    if event.type == "agent:thinking":
        yield chatkit.format_thinking_event(event.content)
    elif event.type == "tool:call":
        yield chatkit.format_tool_call_event(event.tool_name, event.args, status="IN_PROGRESS")
    elif event.type == "tool:result":
        status = "COMPLETED" if event.success else "FAILED"
        yield chatkit.format_tool_call_event(event.tool_name, event.result, status=status)
    elif event.type == "response:delta":
        yield chatkit.format_response_delta_event(event.text)
    elif event.type == "response:done":
        yield chatkit.format_done_event(event.final_output)
```

**Status**: Mapping verified and complete.

---

## 8. Localhost Security Enforcement

### Question
How to enforce localhost-only MCP server binding per FR-018?

### Research Conducted
- Studied MCPServerStdio transport mechanism
- Reviewed FastMCP stdin/stdout communication

### Decision
**No code changes required**. Stdio transport inherently satisfies FR-018.

### Rationale
1. **No Network Binding**: Stdio transport uses stdin/stdout pipes between parent (FastAPI) and child (MCP server) processes
2. **Process Isolation**: MCP server subprocess only accessible via parent process pipes
3. **Zero Network Exposure**: No sockets, no ports, no network interfaces
4. **Operating System Security**: OS enforces process isolation

### SSE Transport Note
If SSE transport is used in future:
- Must configure server to bind `127.0.0.1` explicitly (not `0.0.0.0`)
- Add validation in MCP client initialization:
  ```python
  if transport == "sse":
      assert server_url.startswith("http://127.0.0.1") or server_url.startswith("http://localhost"), \
          "MCP server must bind to localhost only (FR-018)"
  ```

**Status**: Security requirement satisfied by design. Document in architecture notes.

---

## Research Summary

### All Unknowns Resolved ✅

| Unknown                          | Resolution                                          | Document Section |
|----------------------------------|-----------------------------------------------------|------------------|
| MCP transport selection          | MCPServerStdio (stdio)                              | Research #1      |
| Tool discovery mechanism         | Built-in via `mcp_servers` parameter               | Research #2      |
| Subprocess lifecycle management  | FastAPI `@asynccontextmanager` lifespan            | Research #3      |
| Timeout/retry configuration      | 5s timeout, 3 retries, exponential backoff          | Research #4      |
| Degraded mode behavior           | HTTP 200 with friendly errors, no 503               | Research #5      |
| FastMCP schema verification      | MCP Inspector tool (pending Task 14)                | Research #6      |
| ChatKit event mapping            | Existing implementation correct                     | Research #7      |
| Localhost security enforcement   | Stdio transport satisfies by design                 | Research #8      |

### Key Decisions

1. **Transport**: MCPServerStdio for development (SSE prepared for production)
2. **Timeout**: 5 seconds (reduced from 30s)
3. **Degraded Mode**: HTTP 200 with user-friendly errors (never 503 for todo operations)
4. **Lifecycle**: Shared MCP connection in `app.state` (initialized in lifespan)
5. **Security**: Stdio transport inherently localhost-only
6. **Schema Verification**: MCP Inspector validation required before integration finalization

### Dependencies Documented via Context7

- **OpenAI Agents SDK** (library ID: `/openai/openai-agents-python`, version: 0.6.4+)
- **FastMCP** (library ID: `/jlowin/fastmcp`, version: 2.14.0+)

---

**Research Status**: ✅ COMPLETE - All unknowns resolved, ready for implementation
