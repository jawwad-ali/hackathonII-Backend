# Feature Specification: Agent-MCP Integration

**Feature Branch**: `003-agent-mcp-integration`
**Created**: 2025-12-31
**Status**: Draft
**Input**: User description: "Connect the FastAPI Orchestrator to the FastMCP Database Server to enable agentic tool use. Core Purpose: Enable the TodoAgent in the FastAPI server to dynamically discover and execute tools (CRUD operations) hosted on the FastMCP server. This creates a functional bridge between the 'Brain' and the 'Hands.'"

## Clarifications

### Session 2025-12-31

- Q: Who is responsible for starting the MCP server process before the FastAPI orchestrator initializes? → A: FastAPI orchestrator spawns MCP subprocess
- Q: What timeout value (in seconds) should be enforced for MCP tool calls? → A: 5 seconds
- Q: Should the MCP subprocess be restricted to localhost-only communication to prevent unauthorized network access? → A: Yes - Explicitly require localhost-only binding for security
- Q: How many retry attempts should be made for transient MCP failures before giving up? → A: 3 retries
- Q: In degraded mode (when MCP server is unavailable), should the FastAPI server accept user requests? → A: Accept requests but return errors

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Tool Discovery on Startup (Priority: P1)

When the FastAPI orchestrator starts, the TodoAgent must automatically connect to the FastMCP Database Server and discover all available tools. This is the foundational capability that enables all other functionality.

**Why this priority**: Without tool discovery, the agent cannot use any database operations. This is the critical first integration step that unblocks all downstream features.

**Independent Test**: Can be fully tested by starting the FastAPI server and verifying that the TodoAgent logs show successful connection to the MCP server and a list of discovered tools (create_todo, list_todos, update_todo, search_todos, delete_todo).

**Acceptance Scenarios**:

1. **Given** the FastAPI server is not running, **When** the server starts up with a reachable MCP server, **Then** the TodoAgent successfully connects via Stdio transport and logs all discovered tools
2. **Given** the FastAPI server is starting, **When** the MCP server is unreachable or not responding, **Then** the TodoAgent logs a clear error message indicating MCP connectivity failure and the server starts in degraded mode (accepts requests but returns errors for todo operations, health check shows degraded status)
3. **Given** the MCP server exposes 5 CRUD tools, **When** the TodoAgent queries for available tools, **Then** all 5 tools are registered with the agent and available for use

---

### User Story 2 - Agent Executes Tool via MCP Protocol (Priority: P2)

A user interacting with the TodoAgent through the API should be able to trigger CRUD operations that get executed on the remote MCP server. The agent acts as an orchestrator, translating natural language into tool calls.

**Why this priority**: This validates the end-to-end integration and enables actual user value - users can manage todos through natural language.

**Independent Test**: Can be tested by sending a POST request to `/chat/stream` with message "Add a task to buy milk" and verifying that: (1) the agent responds with confirmation, (2) the create_todo tool is called on MCP server, (3) the todo is persisted in the database.

**Acceptance Scenarios**:

1. **Given** a user sends "Add a task to buy milk" via the chat endpoint, **When** the TodoAgent processes the request, **Then** the agent invokes the create_todo tool on the MCP server with title="Buy milk" and returns a success message
2. **Given** a user sends "What are my active tasks?" via the chat endpoint, **When** the TodoAgent processes the request, **Then** the agent invokes the list_todos tool with status filter and returns formatted results
3. **Given** a user sends a complex request like "Create a high-priority task for the dentist appointment", **When** the TodoAgent processes the request, **Then** the agent correctly maps the intent to create_todo with title and priority parameters

---

### User Story 3 - Context Injection for Tool Calls (Priority: P3)

When the agent makes tool calls to the MCP server, it should pass contextual information like thread_id or user_id for logging and tracing purposes. This enables audit trails and debugging.

**Why this priority**: This is important for production observability but not critical for basic functionality. Can be added after core integration works.

**Independent Test**: Can be tested by triggering a tool call and inspecting MCP server logs to verify that context metadata (thread_id, timestamp, etc.) is included in the tool invocation.

**Acceptance Scenarios**:

1. **Given** a user interacts with the TodoAgent in a specific conversation thread, **When** the agent calls any MCP tool, **Then** the thread_id is passed as metadata to the MCP server
2. **Given** the MCP server receives a tool call with context metadata, **When** the tool executes, **Then** the context is logged for observability and debugging

---

### User Story 4 - Graceful Degradation on MCP Failure (Priority: P2)

If the MCP server becomes unavailable during runtime, the TodoAgent should detect the failure and provide helpful error messages to users rather than crashing or hanging.

**Why this priority**: Critical for production resilience. Users should never see cryptic errors or experience crashes due to downstream service failures.

**Independent Test**: Can be tested by stopping the MCP server while the FastAPI server is running, then sending a user request. The agent should return a user-friendly error message like "Unable to access todo database. Please try again later."

**Acceptance Scenarios**:

1. **Given** the MCP server goes down during runtime, **When** the TodoAgent attempts a tool call, **Then** the circuit breaker trips and the agent responds with a clear error message about temporary unavailability (e.g., "Unable to access todo database. Please try again later.") while keeping the server running
2. **Given** the MCP server is unavailable, **When** a user checks the health endpoint, **Then** the health check reports "degraded" status with details about MCP connectivity and the server continues accepting requests
3. **Given** the server is in degraded mode, **When** a user sends any todo-related request, **Then** the server returns HTTP 200 with a user-friendly error message in the response body (not HTTP 503)
4. **Given** the MCP server recovers after being down, **When** the circuit breaker enters half-open state, **Then** the TodoAgent automatically retries and resumes normal operation

---

### User Story 5 - SSE Transport Preparation (Priority: P4)

While Stdio is used for local development, the system should be architected to support Server-Sent Events (SSE) transport for networked MCP server communication in production environments.

**Why this priority**: Low priority for initial implementation but important for production deployment where MCP server may run as a separate service.

**Independent Test**: Can be tested by configuring the agent to use SSE transport instead of Stdio and verifying that tool discovery and execution work identically.

**Acceptance Scenarios**:

1. **Given** the system is configured for SSE transport, **When** the TodoAgent initializes, **Then** it connects to the MCP server via HTTP/SSE on localhost (127.0.0.1) instead of Stdio
2. **Given** SSE transport is in use, **When** tool calls are made, **Then** the behavior is identical to Stdio transport (transparent to the agent logic) and localhost-only binding is maintained

---

### Edge Cases

- What happens when the MCP server responds slowly (>5s)? System enforces 5-second timeout, cancels the request, and returns user-friendly error message (e.g., "Request took too long. Please try again.")
- How does the agent handle malformed tool responses from MCP server? System should catch exceptions and log errors while returning generic error to user
- What if the MCP server is reachable but returns an error for a specific tool call? Agent should parse error message and relay it to user in friendly format
- How does the system handle concurrent requests when MCP server has limited capacity? Circuit breaker and retry logic (3 retries with exponential backoff) should prevent overloading by failing fast after exhausting retries
- What if tool discovery returns zero tools? Agent enters degraded mode (accepts requests but returns errors), logs critical warning, and health check reports degraded status with "No MCP tools available" message

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST spawn FastMCP Database Server as a subprocess on TodoAgent initialization and establish connection using Stdio transport for local development
- **FR-002**: System MUST query the MCP server for available tools during startup and register them dynamically with the TodoAgent
- **FR-003**: System MUST support calling MCP tools (create_todo, list_todos, update_todo, search_todos, delete_todo) from the TodoAgent
- **FR-004**: System MUST pass context metadata (thread_id, timestamp) with every tool call to the MCP server for observability
- **FR-005**: System MUST implement circuit breaker pattern for MCP server connectivity to prevent cascading failures
- **FR-006**: System MUST provide user-friendly error messages when MCP server is unreachable or returns errors
- **FR-007**: System MUST maintain stateless orchestrator design - no local storage of tool execution results
- **FR-008**: System MUST log all MCP tool calls and responses using structured JSON logging
- **FR-009**: System MUST expose health check endpoint that reports MCP server connectivity status
- **FR-010**: System MUST support graceful startup when MCP server is unavailable (degraded mode: server accepts requests but returns user-friendly errors for all todo operations indicating temporary unavailability)
- **FR-011**: System MUST use official OpenAI Agents SDK MCP client (`from agents.mcp import MCPServerStdio`)
- **FR-012**: System MUST support configuration for future SSE transport without agent logic changes
- **FR-013**: System MUST implement retry logic with 3 retry attempts and exponential backoff (e.g., 1s, 2s, 4s delays) for transient MCP failures before circuit breaker activation
- **FR-017**: System MUST enforce a 5-second timeout for all MCP tool calls and return user-friendly error when timeout is exceeded
- **FR-014**: System MUST validate tool call parameters before sending to MCP server
- **FR-015**: System MUST map natural language intents to appropriate MCP tool calls with correct parameters
- **FR-016**: System MUST gracefully terminate the MCP server subprocess on FastAPI shutdown and handle process cleanup
- **FR-018**: System MUST ensure MCP server subprocess binds only to localhost (127.0.0.1) to prevent unauthorized network access

### Key Entities

- **MCP Connection**: Represents the active connection between TodoAgent and FastMCP Database Server, including transport protocol (Stdio/SSE), connection state, and discovered tools
- **Tool Registry**: Collection of available MCP tools discovered at runtime, including tool names, parameter schemas, and descriptions
- **Tool Call Context**: Metadata attached to each MCP tool invocation, including thread_id, user_id (if applicable), timestamp, and request correlation ID
- **Circuit Breaker State**: Tracks MCP server health status (CLOSED/OPEN/HALF-OPEN) and failure/success counts for resilience patterns

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: TodoAgent successfully discovers all 5 CRUD tools from MCP server within 2 seconds of startup
- **SC-002**: Users can execute any todo operation (create, list, update, search, delete) through natural language within 3 seconds end-to-end
- **SC-003**: System provides clear error messages to users within 1 second when MCP server is unavailable
- **SC-004**: Health check endpoint accurately reflects MCP connectivity status with 100% reliability
- **SC-005**: Agent maintains statelessness - no local data storage, all state managed by MCP server and database
- **SC-006**: Circuit breaker trips within 3 failed MCP calls and recovers automatically when service is restored
- **SC-007**: System logs include complete audit trail of all tool calls with context metadata for debugging
- **SC-008**: Agent successfully maps at least 90% of natural language todo requests to correct MCP tool calls
- **SC-009**: Tool discovery process is idempotent - repeated restarts produce identical tool registries
- **SC-010**: System handles concurrent user requests without blocking on MCP calls (async execution)
- **SC-011**: All MCP tool calls that exceed 5 seconds are terminated and return timeout error to user within 5.5 seconds total
- **SC-012**: Transient MCP failures trigger exactly 3 retry attempts with exponential backoff before circuit breaker trips (total 4 attempts: 1 initial + 3 retries)
- **SC-013**: In degraded mode, FastAPI server continues running and accepts requests, returning HTTP 200 with user-friendly error messages for todo operations (never HTTP 503 or crashes)

## Assumptions

1. **MCP Server Lifecycle**: The FastAPI orchestrator spawns the FastMCP Database Server as a subprocess using the command specified in environment configuration (e.g., `uvx fastmcp run src/mcp_server/server.py`). The subprocess lifecycle is managed by the orchestrator.
2. **Tool Stability**: The MCP server's tool interface (tool names and parameter schemas) is stable and versioned. Breaking changes require coordinated updates.
3. **Network Reliability**: For local development, Stdio transport provides reliable communication. For production SSE, standard HTTP retry and timeout strategies apply.
4. **Gemini Model Capability**: Gemini 2.5 Flash can accurately map natural language to tool calls with proper prompting and tool descriptions.
5. **Single MCP Server**: The system connects to exactly one MCP server instance. Multi-server scenarios are out of scope.
6. **No Authentication Between Services**: For initial implementation, no auth required between FastAPI orchestrator and MCP server since both are localhost-only processes. MCP server is restricted to 127.0.0.1 binding to enforce security boundary.
7. **Standard Error Codes**: MCP server returns standardized error responses that can be parsed and relayed to users.
8. **Context Metadata Schema**: Thread ID and timestamp are sufficient context for initial implementation. Additional fields can be added later.
9. **Development Environment**: Stdio transport is sufficient for local development. Production SSE transport is prepared but not required for MVP.
10. **Tool Call Serialization**: MCP protocol handles parameter serialization/deserialization transparently (JSON-RPC format).

## Dependencies

1. **FastMCP Database Server (Feature 002)**: Must have all 5 CRUD tools implemented and tested before integration can begin
2. **OpenAI Agents SDK**: Requires agents.mcp module with MCPServerStdio client for Stdio transport
3. **Circuit Breaker Implementation**: Resilience patterns from existing codebase (src/resilience/circuit_breaker.py and src/resilience/retry.py) must be extended to cover MCP connectivity with 3-retry exponential backoff
4. **Structured Logging**: Observability infrastructure must support logging of MCP tool calls with context metadata
5. **Health Check Endpoint**: Existing /health endpoint must be extended to include MCP connectivity status
6. **Environment Configuration**: .env must support MCP server connection settings (executable path, environment vars, timeout value - default 5 seconds)

## Out of Scope

1. **Multi-MCP Server Support**: Connecting to multiple MCP servers or server discovery
2. **MCP Tool Versioning**: Handling multiple versions of the same tool or tool deprecation strategies
3. **Custom Tool Development**: Creating new MCP tools - only integrating with existing FastMCP Database Server tools
4. **Advanced Context Propagation**: User authentication, multi-tenant context, or complex permission models
5. **Advanced MCP Server Management**: Health monitoring of the MCP subprocess beyond basic process liveness checks, automatic restart strategies, or multi-instance deployment patterns (basic spawn/terminate is in scope)
6. **Performance Optimization**: Caching tool results, batching tool calls, or connection pooling
7. **Alternative Transport Protocols**: WebSocket, gRPC, or other transports beyond Stdio and SSE
8. **Tool Call Analytics**: Detailed metrics on tool usage patterns, success rates per tool, etc.
9. **Request Queuing in Degraded Mode**: Queuing tool calls when MCP server is down for later replay (system returns immediate errors instead)
10. **Dynamic Tool Registration**: Hot-reloading new tools without restarting the TodoAgent

## Notes

- This feature represents Step 3 in the project's integration roadmap (Agent ↔ MCP Integration)
- Critical connectivity milestone: enables the "Brain" (TodoAgent) to control the "Hands" (MCP CRUD tools)
- Success of this feature unblocks Feature 004 (ChatKit ↔ FastAPI Integration) for full end-to-end user experience
- Maximum task count target: 15-18 tasks to ensure rapid implementation
- All implementation must use Gemini 2.5 Flash model (no OpenAI models permitted)
- Circuit breaker configuration should reuse existing patterns from src/resilience/circuit_breaker.py
- Structured logging must follow existing JSON logging format from src/observability/logging.py
