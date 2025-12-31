---
description: "Task breakdown for Agent-MCP Integration feature"
---

# Tasks: Agent-MCP Integration

**Feature Branch**: `003-agent-mcp-integration`
**Input**: Design documents from `/specs/003-agent-mcp-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Integration tests are included per feature requirements.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup & Configuration

**Purpose**: Environment configuration and dependency verification

- [X] T001 Update MCP_SERVER_TIMEOUT from 30s to 5s in src/config.py
- [X] T002 [P] Verify all 5 CRUD tools exist in src/mcp_server/tools/ (create_todo.py, list_todos.py, update_todo.py, search_todos.py, delete_todo.py)
- [X] T003 [P] Update .env.example with MCP_SERVER_TIMEOUT=5 and document required environment variables

---

## Phase 2: Foundational (MCP Connection Infrastructure)

**Purpose**: Core MCP connection management that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create MCP connection initialization function in src/mcp/client.py using MCPServerStdio
- [X] T005 Enhance FastAPI lifespan in src/main.py to initialize MCP connection on startup and store in app.state.mcp_server
- [X] T006 Implement graceful degraded mode handling in lifespan (set app.state.mcp_server = None on failure)
- [X] T007 Add MCP connection logging with initialization time and discovered tools count in src/main.py
- [X] T008 Update /health endpoint in src/api/routes.py to include MCP circuit breaker status and return HTTP 200 with status="degraded" when MCP down

**Checkpoint**: ✅ Foundation ready - MCP connection infrastructure complete, user story implementation can now begin

---

## Phase 3: User Story 1 - Agent Tool Discovery on Startup (Priority: P1) 🎯 MVP

**Goal**: TodoAgent automatically connects to FastMCP Database Server on startup and discovers all 5 available tools (create_todo, list_todos, update_todo, search_todos, delete_todo)

**Independent Test**: Start FastAPI server and verify logs show successful MCP connection with all 5 tools discovered. Health check endpoint returns status="healthy" with MCP circuit breaker state="CLOSED".

### Integration Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Create integration test for MCP connection startup in tests/integration/test_mcp_connection.py (test successful connection, tool discovery count, connection state)
- [X] T010 [P] [US1] Create integration test for MCP connection failure in tests/integration/test_mcp_connection.py (test degraded mode, app.state.mcp_server is None, logs error)
- [X] T011 [P] [US1] Create integration test for health check endpoint in tests/integration/test_mcp_connection.py (test healthy status, degraded status with MCP down)

### Implementation for User Story 1

- [X] T012 [US1] Update src/agents/todo_agent.py to accept mcp_servers parameter and pass to Agent constructor
- [X] T013 [US1] Create agent initialization function in src/api/routes.py that uses app.state.mcp_server
- [X] T014 [US1] Update POST /chat/stream endpoint in src/api/routes.py to check app.state.mcp_server and return degraded mode error if None
- [X] T015 [US1] Add structured logging for tool discovery in src/agents/todo_agent.py (log all discovered tool names)

**Checkpoint**: User Story 1 complete - Agent successfully discovers MCP tools on startup and handles connection failures gracefully

---

## Phase 4: User Story 4 - Graceful Degradation on MCP Failure (Priority: P2)

**Goal**: If MCP server becomes unavailable during runtime, TodoAgent detects failure and provides user-friendly error messages instead of crashing. Circuit breaker pattern prevents cascading failures.

**Independent Test**: Stop MCP server while FastAPI is running, send chat request, verify HTTP 200 response with user-friendly error message (not HTTP 503). Health check shows status="degraded".

**Why P2**: Critical for production resilience - must be implemented early to ensure robust error handling before adding more complex features.

### Integration Tests for User Story 4

- [X] T016 [P] [US4] Create integration test for circuit breaker degradation in tests/integration/test_streaming.py (simulate MCP failure, verify error response format)
- [X] T017 [P] [US4] Create integration test for circuit breaker recovery in tests/integration/test_streaming.py (verify HALF-OPEN state, successful retry)

### Implementation for User Story 4

- [X] T018 [US4] Add CircuitBreakerOpenError exception handling in POST /chat/stream endpoint in src/api/routes.py (return HTTP 200 with degraded error)
- [X] T019 [US4] Update error response format in src/api/schemas.py to include status field (error, degraded)
- [X] T020 [US4] Add retry logic with 3 attempts and exponential backoff for MCP tool calls in src/resilience/retry.py
- [X] T021 [US4] Verify circuit breaker configuration in src/resilience/circuit_breaker.py (5 failures for MCP, 30s recovery timeout)
- [X] T022 [US4] Add logging for circuit breaker state transitions (CLOSED → OPEN → HALF-OPEN → CLOSED) in src/observability/logging.py

**Checkpoint**: User Story 4 complete - System handles MCP failures gracefully with circuit breaker and retry logic

---

## Phase 5: User Story 2 - Agent Executes Tool via MCP Protocol (Priority: P2)

**Goal**: Users can trigger CRUD operations through natural language chat requests. Agent translates intents to MCP tool calls and returns formatted results.

**Independent Test**: Send POST /chat/stream with message "Create a task to buy milk", verify SSE stream includes TOOL_CALL events for create_todo and todo is persisted in database.

### Integration Tests for User Story 2

- [ ] T023 [P] [US2] Create integration test for create_todo tool execution in tests/integration/test_agent_tools.py (verify tool call, database persistence, SSE events)
- [ ] T024 [P] [US2] Create integration test for list_todos tool execution in tests/integration/test_agent_tools.py (verify filtering, result format, SSE events)
- [ ] T025 [P] [US2] Create integration test for SSE event stream format in tests/integration/test_streaming.py (verify THINKING, TOOL_CALL, RESPONSE_DELTA, DONE events)

### Implementation for User Story 2

- [ ] T026 [US2] Verify existing SSE event mapping in src/api/routes.py maps OpenAI Agents SDK events to ChatKit format correctly (agent:thinking → THINKING, tool:call → TOOL_CALL, etc.)
- [ ] T027 [US2] Test agent tool execution with all 5 CRUD operations (create, list, update, search, delete) in development environment
- [ ] T028 [US2] Add tool call validation logging in src/agents/todo_agent.py (log tool name, parameters, execution duration, result status)

**Checkpoint**: User Story 2 complete - Users can manage todos via natural language with full CRUD operations

---

## Phase 6: User Story 3 - Context Injection for Tool Calls (Priority: P3)

**Goal**: Agent passes contextual metadata (thread_id, timestamp, request_id) with every MCP tool call for observability and debugging.

**Independent Test**: Trigger tool call, inspect structured logs to verify context metadata is included in tool invocation logs.

### Integration Tests for User Story 3

- [ ] T029 [P] [US3] Create integration test for context metadata logging in tests/integration/test_agent_tools.py (verify request_id, thread_id, timestamp in logs)

### Implementation for User Story 3

- [ ] T030 [US3] Add context metadata extraction from ChatRequest in src/api/routes.py (extract request_id, generate thread_id if not provided)
- [ ] T031 [US3] Pass context metadata to agent initialization or tool calls in src/agents/todo_agent.py
- [ ] T032 [US3] Update structured logging format in src/observability/logging.py to include request_id, thread_id, tool_name, execution_duration, status for all tool calls

**Checkpoint**: User Story 3 complete - Full observability with context metadata in all tool call logs

---

## Phase 7: User Story 5 - SSE Transport Preparation (Priority: P4)

**Goal**: System architecture supports SSE transport for networked MCP server communication as configuration option (not implemented, just prepared).

**Independent Test**: Review code to verify transport type is configurable (stdio vs sse) without changing agent logic. Document SSE configuration in quickstart.md.

### Implementation for User Story 5

- [ ] T033 [P] [US5] Add MCP_TRANSPORT_TYPE environment variable to src/config.py (default="stdio", allowed values: stdio, sse)
- [ ] T034 [P] [US5] Add conditional transport initialization in src/mcp/client.py (if stdio use MCPServerStdio, if sse document placeholder for future MCPServerSse)
- [ ] T035 [US5] Document SSE transport configuration in specs/003-agent-mcp-integration/quickstart.md (environment variables, localhost-only binding requirement)
- [ ] T036 [US5] Add localhost-only validation comment in src/mcp/client.py for future SSE transport (must bind 127.0.0.1, not 0.0.0.0)

**Checkpoint**: User Story 5 complete - SSE transport prepared for future production deployment

---

## Phase 8: Verification & Documentation

**Purpose**: Final validation and documentation updates

- [ ] T037 [P] Use MCP Inspector to verify FastMCP server JSON-RPC schema (command: uvx fastmcp inspect src/mcp_server/server.py)
- [ ] T038 [P] Run full integration test suite with all user stories (uv run pytest tests/integration/)
- [ ] T039 [P] Verify end-to-end chat request flow (user message → agent → MCP tool → database → SSE response)
- [ ] T040 Update specs/003-agent-mcp-integration/quickstart.md with actual setup commands and usage examples
- [ ] T041 [P] Verify all environment variables documented in .env.example and quickstart.md
- [ ] T042 Run coverage report and ensure >80% for integration code (uv run pytest --cov=src --cov-report=term-missing)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 4 (Phase 4)**: Depends on User Story 1 (Phase 3) - needs connection infrastructure
- **User Story 2 (Phase 5)**: Depends on User Story 1 (Phase 3) and User Story 4 (Phase 4) - needs connection + error handling
- **User Story 3 (Phase 6)**: Depends on User Story 2 (Phase 5) - extends tool execution with metadata
- **User Story 5 (Phase 7)**: Can start after Foundational (Phase 2) - independent preparation
- **Verification (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation → US1 ✅ Can start after Foundational
- **User Story 4 (P2)**: Foundation → US1 → US4 ✅ Needs connection infrastructure from US1
- **User Story 2 (P2)**: Foundation → US1 → US4 → US2 ✅ Needs connection + error handling
- **User Story 3 (P3)**: Foundation → US1 → US4 → US2 → US3 ✅ Extends US2 tool execution
- **User Story 5 (P4)**: Foundation → US5 ✅ Independent preparation (can run in parallel with other stories)

### Critical Path

```
Phase 1: Setup (T001-T003)
    ↓
Phase 2: Foundational (T004-T008) ⚠️ BLOCKS ALL USER STORIES
    ↓
Phase 3: User Story 1 (T009-T015) - Tool Discovery
    ↓
Phase 4: User Story 4 (T016-T022) - Error Handling
    ↓
Phase 5: User Story 2 (T023-T028) - Tool Execution
    ↓
Phase 6: User Story 3 (T029-T032) - Context Metadata
    ↓
Phase 8: Verification (T037-T042)

Phase 7: User Story 5 (T033-T036) - SSE Prep (can run in parallel after Foundational)
```

### Parallel Opportunities

**Within Setup Phase:**
- T002 and T003 can run in parallel (different files)

**Within Foundational Phase:**
- T004, T007, T008 can run in parallel after T005, T006 complete

**Within User Story 1:**
- T009, T010, T011 (all tests) can run in parallel
- T012, T013, T015 can run in parallel (different files)

**Within User Story 4:**
- T016, T017 (tests) can run in parallel
- T018, T019, T020, T021, T022 can run in parallel (different files)

**Within User Story 2:**
- T023, T024, T025 (tests) can run in parallel
- T026, T027, T028 can run in parallel (different aspects)

**Within User Story 3:**
- T030, T031, T032 can run in parallel (different files)

**Within User Story 5:**
- T033, T034, T035, T036 can all run in parallel (different files)

**Within Verification:**
- T037, T038, T039, T041, T042 can run in parallel (independent checks)

---

## Parallel Example: User Story 1 (Tool Discovery)

```bash
# Launch all tests for User Story 1 together:
Task T009: "Integration test for MCP connection startup in tests/integration/test_mcp_connection.py"
Task T010: "Integration test for MCP connection failure in tests/integration/test_mcp_connection.py"
Task T011: "Integration test for health check endpoint in tests/integration/test_mcp_connection.py"

# Launch implementation tasks together (after tests written and failing):
Task T012: "Update src/agents/todo_agent.py to accept mcp_servers parameter"
Task T013: "Create agent initialization function in src/api/routes.py"
Task T015: "Add structured logging for tool discovery in src/agents/todo_agent.py"

# Task T014 runs after T013 completes (depends on agent initialization function)
```

---

## Implementation Strategy

### MVP First (User Stories 1, 4, 2 Only)

**Recommended for fastest delivery:**

1. ✅ Complete Phase 1: Setup (3 tasks)
2. ✅ Complete Phase 2: Foundational (5 tasks) - **CRITICAL BLOCKER**
3. ✅ Complete Phase 3: User Story 1 (7 tasks) - Tool Discovery
4. ✅ Complete Phase 4: User Story 4 (7 tasks) - Error Handling
5. ✅ Complete Phase 5: User Story 2 (6 tasks) - Tool Execution
6. ✅ **STOP and VALIDATE**: Test end-to-end CRUD operations via chat
7. ✅ Complete Phase 8: Verification (6 tasks)
8. 🎉 **MVP COMPLETE** - Deploy/Demo

**Total MVP Tasks**: 34 tasks
**MVP Delivers**: Fully functional agent-MCP integration with all CRUD operations, error handling, and observability

### Full Feature (All User Stories)

**If additional observability and future-proofing desired:**

1. Complete MVP (34 tasks)
2. Add Phase 6: User Story 3 (4 tasks) - Context Metadata
3. Add Phase 7: User Story 5 (4 tasks) - SSE Prep
4. Re-run verification tests

**Total Full Feature Tasks**: 42 tasks

### Incremental Delivery

**Each phase adds value independently:**

1. **Phase 1-2**: Foundation ready → Can manually test MCP connection
2. **+ Phase 3 (US1)**: Agent discovers tools → Can verify in logs
3. **+ Phase 4 (US4)**: Error handling → Can test degraded mode
4. **+ Phase 5 (US2)**: CRUD operations → Users can manage todos! 🎯 **PRIMARY VALUE**
5. **+ Phase 6 (US3)**: Context metadata → Enhanced debugging
6. **+ Phase 7 (US5)**: SSE prep → Future production scaling

---

## Task Summary

**Total Tasks**: 42
**Test Tasks**: 9 (T009-T011, T016-T017, T023-T025, T029)
**Implementation Tasks**: 33

**Tasks by User Story**:
- Setup & Foundational: 8 tasks
- User Story 1 (P1): 7 tasks (3 tests + 4 implementation)
- User Story 4 (P2): 7 tasks (2 tests + 5 implementation)
- User Story 2 (P2): 6 tasks (3 tests + 3 implementation)
- User Story 3 (P3): 4 tasks (1 test + 3 implementation)
- User Story 5 (P4): 4 tasks (0 tests + 4 implementation)
- Verification: 6 tasks

**Parallel Opportunities**: 28 tasks marked [P] can run in parallel within their phases

**MVP Scope**: Phases 1-5 + Phase 8 (34 tasks) delivers full CRUD functionality with error handling

---

## Notes

- All tasks follow checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- [P] tasks operate on different files with no dependencies within their phase
- [Story] labels (US1-US5) map directly to user stories in spec.md
- Each user story is independently completable and testable after Foundational phase
- Tests are written FIRST and must FAIL before implementation begins (TDD approach)
- Circuit breaker and retry logic reuse existing patterns from src/resilience/
- Structured logging follows existing JSON format from src/observability/
- All changes preserve Gemini 2.5 Flash model usage (no OpenAI models)
- Localhost-only security enforced by stdio transport design (no network binding)
- 5-second timeout and 3-retry configuration align with spec requirements

---

**Tasks Status**: ✅ COMPLETE - 42 tasks ready for implementation in priority order
