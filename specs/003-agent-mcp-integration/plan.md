# Implementation Plan: Agent-MCP Integration

**Branch**: `003-agent-mcp-integration` | **Date**: 2025-12-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-agent-mcp-integration/spec.md`

**Note**: This plan follows the `/sp.plan` command workflow and targets 15-18 tasks for rapid implementation.

## Summary

This feature integrates the FastAPI Orchestrator (TodoAgent) with the FastMCP Database Server to enable agentic tool use. The agent will dynamically discover and execute CRUD operations (create_todo, list_todos, update_todo, search_todos, delete_todo) hosted on the MCP server. This creates the critical connectivity bridge between the "Brain" (AI Agent) and the "Hands" (Database Tools).

**Technical Approach**: Use MCPServerStdio transport from OpenAI Agents SDK to spawn the FastMCP server as a subprocess. The agent automatically inherits MCP tools through the `mcp_servers` parameter in the Agent constructor. Implement streaming via ChatKit SSE protocol with comprehensive error handling, circuit breakers, and retry logic for production resilience.

**Current Status**: All 5 MCP CRUD tools are already implemented (Feature 002 complete). Agent infrastructure exists with Gemini integration, circuit breakers, and streaming endpoints. This feature focuses on connecting these components and ensuring robust production-grade integration.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- OpenAI Agents SDK 0.6.4+ (agents.mcp.MCPServerStdio)
- FastMCP 2.14.0+ (MCP server implementation)
- FastAPI 0.115+ (HTTP endpoints)
- AsyncOpenAI (Gemini 2.5 Flash bridge)
- SQLModel 0.0.31+ (ORM)
- Tenacity 9.0.0+ (retry logic)

**Storage**: PostgreSQL with connection pooling (2 min, 8 max overflow)
**Testing**: pytest with async fixtures, integration tests for MCP connectivity
**Target Platform**: Linux/Windows server with local subprocess management
**Project Type**: Web (FastAPI backend with agent orchestration)

**Performance Goals**:
- Tool discovery: <2 seconds on startup
- End-to-end CRUD: <3 seconds (user request → MCP tool → database → response)
- Timeout: 5 seconds for all MCP tool calls
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s)

**Constraints**:
- Localhost-only MCP server binding (127.0.0.1 security boundary)
- Stateless orchestrator (no local data persistence)
- Circuit breaker trips at 3 Gemini failures (60s recovery) and 5 MCP failures (30s recovery)
- Graceful degradation (degraded mode accepts requests but returns user-friendly errors)

**Scale/Scope**:
- Single MCP server instance
- Concurrent request handling with async execution
- 5 CRUD tools (create, list, update, search, delete)
- HTTP streaming with real-time tool tracking

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Environment-First Rule ✅ PASS
- ✅ All commands use `.venv` activation (documented in CLAUDE.md)
- ✅ Dependencies managed via `uv` exclusively
- ✅ `pyproject.toml` declares all dependencies
- **Validation**: No violations detected

### II. Source of Truth Protocol (MCP) ✅ PASS
- ✅ Context7 documentation fetched for OpenAI Agents SDK (library ID: `/openai/openai-agents-python`)
- ✅ Context7 documentation fetched for FastMCP (library ID: `/jlowin/fastmcp`)
- ✅ Documented findings in Technical Context and research.md
- **Validation**: All core dependencies documented via Context7

### III. Pre-Flight Skills Requirement ✅ PASS
- ✅ `/sp.specify` executed (spec.md created with user stories, requirements, success criteria)
- ✅ `/sp.plan` in progress (this document)
- ⏳ `/sp.tasks` pending (next phase after plan approval)
- **Validation**: Skills workflow followed

### IV. uv-Exclusive Package Management ✅ PASS
- ✅ All dependencies in `pyproject.toml`
- ✅ Installation via `uv pip install`
- ✅ Execution via `uv run`
- **Validation**: No pip/poetry/conda usage

### V. Model & Connectivity Architecture ✅ PASS
- ✅ AsyncOpenAI from Agents SDK configured
- ✅ Gemini 2.5 Flash as primary model (via GEMINI_BASE_URL)
- ✅ Environment variables for API keys (no hardcoded secrets)
- **Validation**: Model configuration compliant

### VI. Test-First Development ✅ PASS (Post-Implementation)
- ⏳ Tests will be written for:
  - MCP server connectivity and tool discovery
  - Agent tool execution with circuit breaker scenarios
  - Streaming endpoint with various event types
  - Graceful degradation behavior
- **Validation**: Test requirements documented in tasks.md

### Constitution Compliance Summary
**Status**: ✅ ALL GATES PASSED

No violations requiring justification. All principles adhered to:
- Environment isolation enforced
- MCP documentation fetched and referenced
- Skills workflow executed
- uv package manager exclusively used
- Gemini model architecture confirmed
- Test-first approach documented

## Project Structure

### Documentation (this feature)

```text
specs/003-agent-mcp-integration/
├── spec.md              # Feature specification with user stories
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model (MCP connection state, tool registry)
├── quickstart.md        # Phase 1 usage guide
├── contracts/           # Phase 1 API contracts
│   ├── mcp-connection.json       # MCP connection schema
│   ├── tool-registry.json        # Tool registry schema
│   └── chat-streaming.openapi.yaml # ChatKit SSE endpoint contract
└── tasks.md             # Phase 2 task breakdown (created by /sp.tasks)
```

### Source Code (repository root)

```text
src/
├── main.py                    # FastAPI app with lifespan management
├── config.py                  # Settings with MCP configuration
├── agents/
│   ├── todo_agent.py          # TodoAgent with MCP tools (EXISTS)
│   └── tool_definitions.py    # Tool schemas (EXISTS)
├── api/
│   ├── routes.py              # POST /chat/stream endpoint (EXISTS)
│   └── schemas.py             # Request/response models (EXISTS)
├── mcp/
│   ├── client.py              # MCP connection management (EXISTS - NEEDS ENHANCEMENT)
│   └── config.yaml            # MCP server configuration (EXISTS)
├── mcp_server/
│   ├── server.py              # FastMCP server entry point (EXISTS)
│   ├── models.py              # SQLModel Todo entity (EXISTS)
│   ├── database.py            # PostgreSQL connection (EXISTS)
│   └── tools/                 # All 5 CRUD tools (EXISTS)
│       ├── create_todo.py
│       ├── list_todos.py
│       ├── update_todo.py
│       ├── search_todos.py
│       └── delete_todo.py
├── resilience/
│   ├── circuit_breaker.py     # Circuit breaker pattern (EXISTS)
│   └── retry.py               # Retry decorators (EXISTS)
├── observability/
│   ├── logging.py             # Structured JSON logging (EXISTS)
│   └── metrics.py             # Metrics tracking (EXISTS)
└── streaming/
    └── chatkit.py             # ChatKit SSE formatters (EXISTS)

tests/
├── mcp_server/
│   ├── conftest.py            # Pytest fixtures (EXISTS)
│   ├── test_models.py         # Model tests (EXISTS)
│   └── test_tools.py          # Tool integration tests (EXISTS)
└── integration/
    ├── test_mcp_connection.py # NEW: MCP connectivity tests
    ├── test_agent_tools.py    # NEW: Agent tool execution tests
    └── test_streaming.py      # NEW: ChatKit streaming tests
```

**Structure Decision**: Single project structure (Option 1) selected. Backend-only application with agent orchestration. All components colocated under `src/` with clear separation of concerns:
- `agents/` - AI agent logic
- `api/` - HTTP endpoints
- `mcp/` - MCP client integration
- `mcp_server/` - MCP server implementation
- `resilience/` - Production patterns
- `observability/` - Logging and metrics
- `streaming/` - ChatKit protocol

## Complexity Tracking

**Status**: No Constitution violations to justify.

All complexity is justified by functional requirements:
- **Dual Circuit Breakers**: Required by FR-005 (MCP + Gemini resilience)
- **Retry Logic**: Required by FR-013 (3 retries with exponential backoff)
- **Streaming Protocol**: Required by ChatKit integration (User Story 2)
- **Graceful Degradation**: Required by FR-010 and User Story 4

No unnecessary abstractions introduced. Design follows principle of least complexity.

---

# Phase 0: Research & Discovery

## Research Findings

### 1. OpenAI Agents SDK MCP Integration Patterns

**Source**: Context7 - `/openai/openai-agents-python`

**Key Findings**:

1. **MCPServerStdio Transport**:
   - Connects to MCP servers via subprocess using stdin/stdout
   - Spawns server process with `command` and `args` parameters
   - Automatic process lifecycle management (spawn on connect, terminate on close)
   - Example pattern:
     ```python
     async with MCPServerStdio(
         name="Filesystem Server",
         params={
             "command": "npx",
             "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir]
         }
     ) as server:
         agent = Agent(
             name="Assistant",
             instructions="Use the tools to answer questions.",
             mcp_servers=[server]
         )
     ```

2. **Dynamic Tool Discovery**:
   - Tools are automatically registered when `mcp_servers` parameter is passed to Agent constructor
   - No manual tool registration required
   - Agent inherits all tools exposed by the MCP server
   - Tools appear in agent's tool list with names, descriptions, and schemas from MCP server

3. **Tool Filtering** (Optional):
   - `tool_filter` parameter allows conditional tool exposure
   - Receives `ToolFilterContext` with agent metadata
   - Useful for restricting dangerous tools based on agent role
   - Example:
     ```python
     async def context_aware_filter(context: ToolFilterContext, tool) -> bool:
         if context.agent.name == "Code Reviewer" and tool.name.startswith("danger_"):
             return False
         return True
     ```

4. **Integration Options**:
   - **stdio** (MCPServerStdio): Local subprocess, stdin/stdout communication (chosen for development)
   - **SSE** (MCPServerSse): HTTP with Server-Sent Events (prepared for production)
   - **Streamable HTTP** (MCPServerStreamableHttp): HTTP streaming
   - **Hosted MCP**: OpenAI Responses API calls MCP server on model's behalf

**Decision**: Use **MCPServerStdio** for primary implementation with localhost-only binding. SSE transport prepared as configuration option for production deployment.

**Rationale**: Stdio provides reliable local communication with process lifecycle management. No network overhead. SSE allows future scaling to separate MCP server instance.

### 2. FastMCP Server Best Practices

**Source**: Context7 - `/jlowin/fastmcp`

**Key Findings**:

1. **Tool Registration**:
   - `@mcp.tool` decorator exposes functions as MCP tools
   - Function name becomes tool name (customizable via `name` parameter)
   - Docstring becomes tool description for LLM
   - Type hints generate JSON schema for parameters automatically
   - Example:
     ```python
     @mcp.tool
     def multiply(a: float, b: float) -> float:
         """Multiplies two numbers together."""
         return a * b
     ```

2. **Tool Configuration**:
   - `name`: Override function name
   - `description`: Override docstring
   - `tags`: Categorize tools for filtering
   - `enabled`: Conditionally enable/disable tools
   - `annotations`: Metadata hints (readonly, destructive, idempotent, openWorld)
   - `meta`: Custom metadata passed to client
   - Example:
     ```python
     @mcp.tool(
         name="find_products",
         description="Search the product catalog.",
         tags={"catalog", "search"},
         meta={"version": "1.2"}
     )
     ```

3. **Parameter Validation**:
   - FastMCP validates inputs against JSON schema derived from type hints
   - Invalid parameters rejected before function execution
   - Type coercion handled automatically (str → int, etc.)

4. **Server Execution**:
   - Server runs via `uvx fastmcp run server.py` command
   - Communicates via stdin/stdout for stdio transport
   - JSON-RPC protocol handled transparently

**Decision**: Existing MCP server implementation (`src/mcp_server/`) follows these patterns correctly. All 5 tools use `@mcp.tool` decorator with proper type hints and docstrings.

**Verification Required**: Use MCP Inspector to confirm JSON-RPC schema before integration.

### 3. MCP Connection Lifecycle Management

**Research Question**: How should the FastAPI orchestrator manage the MCP server subprocess lifecycle?

**Findings**:

1. **FastAPI Lifespan Events**:
   - Use `@asynccontextmanager` lifespan for startup/shutdown hooks
   - Initialize MCP connection on startup
   - Terminate subprocess on shutdown
   - Example pattern:
     ```python
     @asynccontextmanager
     async def lifespan(app: FastAPI):
         # Startup
         mcp_server = await initialize_mcp_connection()
         yield {"mcp_server": mcp_server}
         # Shutdown
         await mcp_server.close()
     ```

2. **Context Sharing**:
   - Store MCP server instance in app.state for endpoint access
   - Pass to agent creation function in routes
   - Ensure single connection per application instance

3. **Error Handling**:
   - If MCP server fails to start, log error and enter degraded mode
   - Health check endpoint reports MCP connectivity status
   - Circuit breaker prevents cascading failures

**Decision**: Enhance existing `lifespan` in `src/main.py` to initialize MCP connection on startup and store in `app.state.mcp_server`. Update `/chat/stream` endpoint to use shared connection instead of creating new one per request.

**Rationale**: Reusing connection reduces subprocess overhead. Single connection simplifies lifecycle management and state tracking.

### 4. Streaming & ChatKit Protocol Alignment

**Research Question**: How to map OpenAI Agents SDK events to ChatKit SSE format?

**Findings**:

1. **Agents SDK Event Types** (from `Runner.run_streamed()`):
   - `agent:thinking` - Agent reasoning
   - `tool:call` - Tool invocation started
   - `tool:result` - Tool execution completed
   - `response:delta` - Streaming text response
   - `response:done` - Final response

2. **ChatKit SSE Event Types** (existing implementation in `src/streaming/chatkit.py`):
   - `THINKING` - Agent reasoning state
   - `TOOL_CALL` - Tool execution in progress
   - `RESPONSE_DELTA` - Incremental text
   - `ERROR` - Error occurred
   - `DONE` - Stream complete

3. **Mapping Logic** (already implemented in `src/api/routes.py`):
   - `agent:thinking` → `THINKING` event
   - `tool:call` → `TOOL_CALL` event (IN_PROGRESS status)
   - `tool:result` → `TOOL_CALL` event (COMPLETED/FAILED status)
   - `response:delta` → `RESPONSE_DELTA` event
   - `response:done` → `DONE` event

**Decision**: Existing mapping in `src/streaming/chatkit.py` and `src/api/routes.py` is correct. No changes required.

**Verification**: Test streaming endpoint with MCP tool calls to ensure events flow correctly.

### 5. Timeout & Retry Configuration

**Research Question**: What timeout and retry values align with spec requirements?

**Spec Requirements**:
- **FR-017**: 5-second timeout for MCP tool calls
- **FR-013**: 3 retry attempts with exponential backoff
- **SC-011**: Tool calls exceeding 5s terminated within 5.5s total

**Current Implementation** (from `src/config.py`):
- MCP server timeout: 30 seconds (too high)
- Retry attempts: 3 (correct)
- Exponential backoff: 1s, 2s, 4s delays (correct)

**Decision**: Update `MCP_SERVER_TIMEOUT` default from 30s to 5s in `src/config.py` to align with FR-017.

**Rationale**: 30-second timeout violates SC-011 (5.5s total). Reducing to 5s ensures tool calls fail fast and don't block user requests.

### 6. Localhost-Only Security Binding

**Research Question**: How to enforce localhost-only MCP server binding?

**Spec Requirement**:
- **FR-018**: MCP server subprocess binds only to localhost (127.0.0.1)

**FastMCP Behavior**:
- Stdio transport uses stdin/stdout (no network binding)
- No external network exposure by design
- Process only accessible via parent process pipes

**Decision**: Stdio transport inherently satisfies FR-018. Document this as a security property in architecture docs.

**SSE Transport Note**: If SSE is used, must configure server to bind `0.0.0.0` → `127.0.0.1` explicitly. Add validation in MCP client initialization.

### 7. Degraded Mode Behavior

**Research Question**: What should the system do when MCP server is unavailable?

**Spec Requirements**:
- **FR-010**: Graceful startup when MCP unavailable (degraded mode)
- **User Story 4**: Accept requests but return user-friendly errors
- **SC-013**: Return HTTP 200 with error messages (not HTTP 503)

**Current Implementation**:
- Circuit breaker trips after 5 MCP failures
- Health check returns 503 when both circuit breakers open (violates SC-013)
- No explicit degraded mode handling

**Decision**:
1. Update `/chat/stream` to catch MCP circuit breaker exceptions and return HTTP 200 with user-friendly error message in response body
2. Update `/health` to return HTTP 200 with `status: "degraded"` when MCP circuit breaker is open (Gemini open → 503 is acceptable)
3. Log degraded mode transitions for alerting

**Rationale**: Users should never see 503 for todo operations. Degraded mode provides better UX than service unavailable.

---

# Phase 1: Design & Contracts

## Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**Key Entities**:

1. **MCP Connection** (runtime state, not persisted):
   - Transport type (stdio/sse)
   - Process handle (for stdio)
   - Connection state (connected/disconnected/degraded)
   - Last health check timestamp

2. **Tool Registry** (runtime state, not persisted):
   - Tool name
   - Tool description
   - Parameter schema (JSON Schema)
   - Metadata (tags, version)

3. **Tool Call Context** (request-scoped):
   - Request ID (correlation)
   - Thread ID (conversation tracking)
   - Tool name
   - Parameters
   - Execution start time
   - Execution duration
   - Result or error

4. **Circuit Breaker State** (global state):
   - Service name (mcp/gemini)
   - State (CLOSED/OPEN/HALF-OPEN)
   - Failure count
   - Last failure timestamp
   - Recovery timeout

## API Contracts

See [contracts/](./contracts/) for OpenAPI/JSON Schema definitions.

**Key Endpoints**:

1. **POST /chat/stream** (existing - no changes):
   - Request: `ChatRequest` with message and optional request_id
   - Response: SSE stream with ChatKit events (THINKING, TOOL_CALL, RESPONSE_DELTA, ERROR, DONE)
   - Status codes: 200 (success or degraded mode error), 429 (rate limit), 500 (internal error)

2. **GET /health** (existing - requires update):
   - Response: Health status with circuit breaker states, uptime, metrics
   - Status codes:
     - 200 (healthy or degraded - MCP down, Gemini up)
     - 503 (critical failure - Gemini down)

## Implementation Strategy

### Task Breakdown (15-18 tasks target)

**Phase 1: MCP Connection Setup (5 tasks)**
1. Update `src/config.py` to reduce MCP timeout from 30s to 5s
2. Enhance `src/main.py` lifespan to initialize MCP connection on startup
3. Store MCP server instance in `app.state` for reuse
4. Add MCP connection health check to `/health` endpoint
5. Implement graceful degraded mode handling in `lifespan`

**Phase 2: Agent Integration (4 tasks)**
6. Update `src/api/routes.py` to use shared MCP connection from `app.state`
7. Verify dynamic tool discovery from MCP server in agent initialization
8. Test agent tool execution with all 5 CRUD operations
9. Validate tool call context metadata (thread_id, timestamps) in logs

**Phase 3: Error Handling & Resilience (4 tasks)**
10. Update `/chat/stream` to catch MCP circuit breaker exceptions and return HTTP 200 with user-friendly errors
11. Update `/health` to return HTTP 200 with `status: "degraded"` when MCP circuit breaker is open
12. Verify retry logic (3 attempts, exponential backoff) for transient MCP failures
13. Test circuit breaker transitions (CLOSED → OPEN → HALF-OPEN → CLOSED)

**Phase 4: Verification & Documentation (4 tasks)**
14. Use MCP Inspector to verify FastMCP server JSON-RPC schema
15. Integration test: End-to-end chat request → agent → MCP tool → database → response
16. Integration test: Graceful degradation (MCP server down, user receives friendly error)
17. Update quickstart.md with setup instructions and usage examples

**Total Tasks**: 17 (within 15-18 target)

## Quickstart

See [quickstart.md](./quickstart.md) for complete setup and usage guide.

**Summary**:
1. Activate `.venv` and install dependencies via `uv`
2. Configure `.env` with Gemini API key and database URL
3. Start FastAPI server: `uv run uvicorn src.main:app --reload`
4. Verify MCP connection: `GET /health` (check `mcp_circuit_breaker` state)
5. Send chat request: `POST /chat/stream` with message "Create a task to buy groceries"
6. Observe SSE stream with TOOL_CALL events for `create_todo`

---

# Phase 2: Task Generation

**Output**: See [tasks.md](./tasks.md) (created by `/sp.tasks` command)

**Note**: This plan stops at Phase 1. The `/sp.tasks` command will generate the detailed task breakdown with acceptance criteria, dependencies, and test requirements.

---

# Appendices

## A. MCP Documentation References

**OpenAI Agents SDK**:
- Library ID: `/openai/openai-agents-python`
- Version: 0.6.4+
- Key Modules: `agents.mcp.MCPServerStdio`, `agents.Agent`, `agents.Runner`
- Documentation: https://github.com/openai/openai-agents-python/blob/main/docs/mcp.md

**FastMCP**:
- Library ID: `/jlowin/fastmcp`
- Version: 2.14.0+
- Key Decorators: `@mcp.tool`
- Documentation: https://github.com/jlowin/fastmcp/blob/main/docs/

## B. Environment Variables

Required additions to `.env`:

```env
# MCP Server Configuration (update timeout)
MCP_SERVER_TIMEOUT=5  # Changed from 30 to align with FR-017

# Existing variables (no changes)
DATABASE_URL=postgresql://user:password@localhost:5432/todo_db
GEMINI_API_KEY=your_gemini_api_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash
```

## C. Testing Strategy

**Integration Tests** (new test files required):

1. **test_mcp_connection.py**:
   - Test MCP server startup and connection
   - Test tool discovery (verify all 5 tools registered)
   - Test connection failure handling (degraded mode)
   - Test subprocess lifecycle (startup/shutdown)

2. **test_agent_tools.py**:
   - Test agent executes `create_todo` via MCP
   - Test agent executes `list_todos` via MCP
   - Test agent executes `update_todo` via MCP
   - Test agent executes `search_todos` via MCP
   - Test agent executes `delete_todo` via MCP
   - Test tool call timeout (5s limit)
   - Test tool call retry (3 attempts)

3. **test_streaming.py**:
   - Test SSE event stream for successful tool call
   - Test TOOL_CALL event with IN_PROGRESS status
   - Test TOOL_CALL event with COMPLETED status
   - Test ERROR event for MCP circuit breaker failure
   - Test degraded mode error response (HTTP 200 with error message)

**Target Coverage**: >80% for new integration code

## D. Rollout Plan

**Phase 1: Local Development**
- Complete implementation and testing
- Verify with MCP Inspector
- Run integration tests

**Phase 2: Staging Deployment**
- Deploy to staging environment
- Monitor circuit breaker behavior
- Test degraded mode in staging

**Phase 3: Production Deployment**
- Deploy with feature flag (optional)
- Monitor metrics (tool call latency, success rate)
- Gradual rollout to 100% traffic

**Phase 4: SSE Transport Preparation**
- Configure SSE transport as environment variable
- Test SSE connectivity in staging
- Document SSE deployment for production scale

---

**Plan Status**: ✅ COMPLETE - Ready for `/sp.tasks` execution

**Next Steps**:
1. User reviews and approves this plan
2. Run `/sp.tasks` to generate task breakdown
3. Begin implementation following task order
