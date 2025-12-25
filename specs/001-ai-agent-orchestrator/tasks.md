# Tasks: AI Agent Orchestrator for Todo Management

**Feature**: 001-ai-agent-orchestrator
**Input**: Design documents from `/specs/001-ai-agent-orchestrator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not requested in specification - Test tasks are EXCLUDED per template guidance.

**Organization**: Tasks are grouped by implementation phases aligned with TASK_PROMPT.md and user stories from spec.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Environment & Boilerplate

**Purpose**: Initialize project using uv and create basic FastAPI structure

- [X] T001 Initialize project with uv creating .venv in project root
- [X] T002 Create pyproject.toml with dependencies: fastapi, openai-agents-python, agents-mcp, openai, pydantic, uvicorn, python-dotenv, tenacity, pythonjsonlogger
- [X] T003 Install dependencies using uv pip install -e . command
- [X] T004 Create src/ directory structure with subdirectories: agents/, api/, mcp/, streaming/, observability/, resilience/
- [X] T005 [P] Create .env.example file with Gemini API and MCP server configuration template
- [X] T006 [P] Create .gitignore with .env and .venv entries
- [X] T007 Create src/main.py with basic FastAPI app initialization and /health endpoint returning {"status": "healthy"}
- [X] T008 Create src/config.py with environment variable loading using python-dotenv for Gemini and MCP configuration
- [X] T009 Create mcp_agent.config.yaml with todo_server MCP configuration
- [ ] T010 [P] Create Dockerfile with multi-stage build using python:3.11-slim-bookworm base image
- [ ] T011 [P] Create docker-compose.yml with orchestrator, mcp-server, and postgres services

---

## Phase 2: Gemini Bridge (The Brain)

**Purpose**: Implement AsyncOpenAI client targeting Gemini 2.5 Flash and TodoAgent using OpenAI Agents SDK

- [X] T012 Create src/agents/__init__.py empty module file
- [X] T013 Implement AsyncOpenAI client configuration in src/config.py with Gemini base_url and API key from environment
- [X] T014 Create src/agents/todo_agent.py with TodoAgent definition using OpenAI Agents SDK
- [X] T015 Implement set_default_openai_client() call in src/agents/todo_agent.py with Gemini-configured AsyncOpenAI
- [X] T016 Define TodoAgent system instructions in src/agents/todo_agent.py emphasizing intent extraction and MCP tool usage without internal database logic

---

## Phase 3: MCP Client (The Hands)

**Purpose**: Set up MCP Client within FastAPI connecting to FastMCP server and dynamically register MCP tools to TodoAgent

- [X] T017 Create src/mcp/__init__.py empty module file
- [X] T018 Create src/mcp/client.py with agents_mcp RunnerContext initialization using mcp_agent.config.yaml
- [X] T019 Implement dynamic MCP tool discovery in src/mcp/client.py connecting to todo_server
- [X] T020 Update src/agents/todo_agent.py to register discovered MCP tools (create_todo, list_todos, update_todo, delete_todo)
- [X] T021 Create src/agents/tool_definitions.py documenting expected MCP tool schemas for reference

---

## Phase 4: ChatKit Streaming

**Purpose**: Implement /api/chatkit endpoint with streaming response including Thinking blocks and Tool Call status events

- [X] T022 Create src/api/__init__.py empty module file
- [X] T023 Create src/api/schemas.py with ChatRequest Pydantic model including input validation (1-5000 chars, UTF-8, control character stripping)
- [X] T024 Create src/streaming/__init__.py empty module file
- [X] T025 Create src/streaming/chatkit.py with SSE event formatters for thinking, tool_call, response_delta, error, done events
- [X] T026 Create src/api/routes.py with POST /chat/stream endpoint using StreamingResponse media_type="text/event-stream"
- [X] T027 Implement async generator in src/api/routes.py calling Runner.run_streamed() with TodoAgent and MCP context
- [X] T028 Map OpenAI Agents SDK stream events to ChatKit SSE format in src/streaming/chatkit.py
- [X] T029 Integrate streaming endpoint in src/main.py by including router from src/api/routes.py

---

## Phase 5: Resilience Implementation (Circuit Breaker & Retry)

**Purpose**: Implement exponential backoff retry logic and circuit breaker pattern for external dependencies per FR-012

- [X] T030 Create src/resilience/__init__.py empty module file
- [X] T031 Create src/resilience/circuit_breaker.py with CircuitBreakerState and CircuitBreakerConfig dataclasses
- [X] T032 Implement circuit breaker state machine (closed → open → half_open) in src/resilience/circuit_breaker.py
- [X] T033 Create src/resilience/retry.py with tenacity exponential backoff configuration for MCP and Gemini calls
- [X] T034 Wrap MCP client calls in src/mcp/client.py with circuit breaker and retry logic
- [X] T035 Wrap AsyncOpenAI calls in src/agents/todo_agent.py with circuit breaker and retry logic
- [X] T036 Update /health endpoint in src/main.py to include circuit breaker states and metrics per openapi.yaml HealthResponse schema

---

## Phase 6: Observability (Structured Logging)

**Purpose**: Implement structured JSON logging with request IDs for correlation per FR-011

- [X] T037 Create src/observability/__init__.py empty module file
- [X] T038 Create src/observability/logging.py with python-json-logger configuration for JSON structured logs
- [X] T039 Implement request ID generation middleware in src/observability/logging.py using uuid
- [X] T040 Add request ID to logging context for all log entries in src/observability/logging.py
- [X] T041 Create src/observability/metrics.py with timing metrics tracking for request_received, mcp_tool_called, gemini_api_called, request_completed events
- [X] T042 Integrate structured logging in src/main.py FastAPI application startup
- [X] T043 Add X-Request-ID header to streaming responses in src/api/routes.py

---

## Phase 7: User Story 1 - Create Todo from Natural Language (Priority: P1) 🎯 MVP

**Goal**: Convert natural language create requests into structured MCP create_todo tool calls

**Independent Test**: Send "Remind me to buy eggs tomorrow at 3pm" to /chat/stream and verify create_todo MCP tool is called with correct parameters

**Acceptance Criteria**: SC-001 (95% intent accuracy), SC-002 (zero crashes), SC-003 (<2s first token), SC-005 (90% attribute extraction)

### Implementation for User Story 1

- [X] T044 [US1] Update TodoAgent system instructions in src/agents/todo_agent.py to extract title, due_date, priority from natural language for create operations
- [X] T045 [US1] Implement create intent detection logic in streaming handler in src/api/routes.py
- [X] T046 [US1] Add error handling for create_todo MCP tool failures in src/api/routes.py with user-friendly error messages
- [X] T047 [US1] Stream thinking event showing parameter extraction reasoning in src/api/routes.py
- [X] T048 [US1] Stream tool_call event with create_todo and extracted arguments in src/api/routes.py
- [X] T049 [US1] Stream response_delta events with confirmation message in src/api/routes.py
- [X] T050 [US1] Stream done event with final_output and tools_called=["create_todo"] in src/api/routes.py
- [X] T051 [US1] Log mcp_tool_called event with create_todo details in src/api/routes.py

**Checkpoint**: User Story 1 complete - can create todos from natural language with streaming feedback

---

## Phase 8: User Story 2 - Query and List Todos (Priority: P2)

**Goal**: Convert natural language queries into structured MCP list_todos tool calls with filters

**Independent Test**: Send "What's on my todo list for today?" to /chat/stream and verify list_todos MCP tool is called with due_date_filter="today"

**Acceptance Criteria**: SC-001 (95% intent accuracy), SC-002 (zero crashes), SC-005 (90% filter extraction)

### Implementation for User Story 2

- [ ] T052 [US2] Update TodoAgent system instructions in src/agents/todo_agent.py to extract status, priority, due_date_filter, tags from natural language for list operations
- [ ] T053 [US2] Implement list intent detection logic in streaming handler in src/api/routes.py
- [ ] T054 [US2] Add error handling for list_todos MCP tool failures in src/api/routes.py with user-friendly error messages
- [ ] T055 [US2] Stream thinking event showing filter extraction reasoning in src/api/routes.py
- [ ] T056 [US2] Stream tool_call event with list_todos and extracted filter arguments in src/api/routes.py
- [ ] T057 [US2] Format list_todos results into natural language response in src/api/routes.py
- [ ] T058 [US2] Stream response_delta events with formatted todo list in src/api/routes.py
- [ ] T059 [US2] Stream done event with final_output and tools_called=["list_todos"] in src/api/routes.py
- [ ] T060 [US2] Log mcp_tool_called event with list_todos details in src/api/routes.py

**Checkpoint**: User Stories 1 AND 2 complete - can create and query todos independently

---

## Phase 9: User Story 3 - Update Todo Items (Priority: P3)

**Goal**: Convert natural language update requests into structured MCP update_todo tool calls

**Independent Test**: Create a todo, then send "Mark buy eggs as complete" to /chat/stream and verify update_todo MCP tool is called with status="completed"

**Acceptance Criteria**: SC-001 (95% intent accuracy), SC-002 (zero crashes), SC-005 (90% attribute extraction)

### Implementation for User Story 3

- [ ] T061 [US3] Update TodoAgent system instructions in src/agents/todo_agent.py to extract todo_id, updated fields from natural language for update operations
- [ ] T062 [US3] Implement update intent detection logic in streaming handler in src/api/routes.py
- [ ] T063 [US3] Add context inference for todo_id from recent conversation or list results in src/api/routes.py
- [ ] T064 [US3] Add error handling for update_todo MCP tool failures in src/api/routes.py with user-friendly error messages
- [ ] T065 [US3] Stream thinking event showing todo_id inference and field extraction reasoning in src/api/routes.py
- [ ] T066 [US3] Stream tool_call event with update_todo and extracted arguments in src/api/routes.py
- [ ] T067 [US3] Stream response_delta events with update confirmation message in src/api/routes.py
- [ ] T068 [US3] Stream done event with final_output and tools_called=["update_todo"] in src/api/routes.py
- [ ] T069 [US3] Log mcp_tool_called event with update_todo details in src/api/routes.py

**Checkpoint**: User Stories 1, 2, AND 3 complete - can create, query, and update todos independently

---

## Phase 10: User Story 4 - Delete Todos with Guardrails (Priority: P4)

**Goal**: Convert natural language delete requests into structured MCP delete_todo tool calls with confirmation for mass deletions

**Independent Test**: Create todos, send "Delete the buy eggs task" (single) and verify immediate deletion, send "Clear all completed tasks" (mass) and verify confirmation request

**Acceptance Criteria**: SC-001 (95% intent accuracy), SC-002 (zero crashes), SC-004 (100% mass deletion confirmation), SC-005 (90% attribute extraction)

### Implementation for User Story 4

- [ ] T070 [US4] Update TodoAgent system instructions in src/agents/todo_agent.py to detect single vs mass deletion operations
- [ ] T071 [US4] Implement delete intent detection logic in streaming handler in src/api/routes.py
- [ ] T072 [US4] Add mass deletion detection (3+ todos) in src/api/routes.py
- [ ] T073 [US4] Implement confirmation request streaming for mass deletions in src/api/routes.py showing count and waiting for user approval
- [ ] T074 [US4] Add confirmation parsing logic for user responses ("yes, delete all") in src/api/routes.py
- [ ] T075 [US4] Add error handling for delete_todo MCP tool failures in src/api/routes.py with user-friendly error messages
- [ ] T076 [US4] Stream thinking event showing deletion scope and safety check reasoning in src/api/routes.py
- [ ] T077 [US4] Stream tool_call event with delete_todo and confirmation=true in src/api/routes.py
- [ ] T078 [US4] Stream response_delta events with deletion confirmation or warning message in src/api/routes.py
- [ ] T079 [US4] Stream done event with final_output and tools_called=["delete_todo"] in src/api/routes.py
- [ ] T080 [US4] Log mcp_tool_called event with delete_todo details in src/api/routes.py

**Checkpoint**: All user stories complete - full CRUD functionality with safety guardrails

---

## Phase 11: Edge Cases & Error Handling

**Purpose**: Handle ambiguous input, out-of-scope requests, tool failures, timeouts per spec edge cases

- [ ] T081 [P] Implement ambiguous input detection in src/api/routes.py streaming clarifying questions when intent unclear
- [ ] T082 [P] Implement out-of-scope request detection in src/api/routes.py informing user of todo-only capabilities
- [ ] T083 [P] Add MCP server timeout handling (30s) in src/mcp/client.py with streaming status updates
- [ ] T084 [P] Add Gemini API timeout handling in src/agents/todo_agent.py with retry and circuit breaker fallback
- [ ] T085 Implement graceful degradation error messages in src/api/routes.py when circuit breakers open per FR-012
- [ ] T086 Update /health endpoint in src/main.py to return 503 when both circuit breakers open per openapi.yaml
- [ ] T087 Add input sanitization validation in src/api/schemas.py with control character stripping and UTF-8 validation per FR-013

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [ ] T088 [P] Add comprehensive logging for all agent reasoning steps in src/api/routes.py
- [ ] T089 [P] Add performance metrics tracking for total_requests, successful_requests, failed_requests in src/observability/metrics.py
- [ ] T090 [P] Update README.md with quickstart instructions referencing specs/001-ai-agent-orchestrator/quickstart.md
- [ ] T091 Verify Docker build succeeds with docker build -t ai-agent-orchestrator:latest .
- [ ] T092 Verify docker-compose up succeeds with all services starting
- [ ] T093 Run manual validation of quickstart.md steps from project setup through endpoint testing
- [ ] T094 Verify /health endpoint returns circuit_breakers status and metrics per openapi.yaml
- [ ] T095 Verify structured JSON logs are written with request_id correlation
- [ ] T096 [P] Code cleanup and remove any unused imports or placeholder code
- [ ] T097 [P] Add docstrings to all public functions in src/agents/, src/api/, src/mcp/, src/streaming/, src/resilience/, src/observability/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Environment & Boilerplate)**: No dependencies - can start immediately
- **Phase 2 (Gemini Bridge)**: Depends on Phase 1 completion (T001-T011)
- **Phase 3 (MCP Client)**: Depends on Phase 2 completion (T012-T016)
- **Phase 4 (ChatKit Streaming)**: Depends on Phase 3 completion (T017-T021)
- **Phase 5 (Resilience)**: Depends on Phase 3 completion (T017-T021) - Can run in parallel with Phase 4
- **Phase 6 (Observability)**: Depends on Phase 1 completion (T001-T011) - Can run in parallel with Phases 2-5
- **Phase 7 (User Story 1)**: Depends on Phases 1-6 completion (T001-T043) - BLOCKS all other user stories
- **Phase 8 (User Story 2)**: Depends on Phase 7 completion (T044-T051)
- **Phase 9 (User Story 3)**: Depends on Phase 7 completion (T044-T051) - Can run in parallel with Phase 8
- **Phase 10 (User Story 4)**: Depends on Phase 7 completion (T044-T051) - Can run in parallel with Phases 8-9
- **Phase 11 (Edge Cases)**: Depends on Phases 7-10 completion (T044-T080)
- **Phase 12 (Polish)**: Depends on all previous phases completion

### User Story Dependencies

- **User Story 1 (P1 - T044-T051)**: MVP baseline - MUST complete first before any other stories
- **User Story 2 (P2 - T052-T060)**: Depends on US1 completion - Can start after T051
- **User Story 3 (P3 - T061-T069)**: Depends on US1 completion - Can run in parallel with US2
- **User Story 4 (P4 - T070-T080)**: Depends on US1 completion - Can run in parallel with US2/US3

### Within Each Phase

- Tasks marked [P] can run in parallel (different files, no dependencies)
- Sequential tasks must complete in order (e.g., T001 → T002 → T003)
- User Story tasks within same phase can run in parallel if marked [P]

### Parallel Opportunities

**Phase 1 (Setup)**:
- T005 (.env.example) || T006 (.gitignore) || T010 (Dockerfile) || T011 (docker-compose.yml)

**Phase 5 (Resilience)**:
- T030-T035 can run while Phase 4 is in progress (different modules)

**Phase 6 (Observability)**:
- T037-T041 can run in parallel with Phases 2-5 (different modules)

**Phase 11 (Edge Cases)**:
- T081 (ambiguous) || T082 (out-of-scope) || T083 (MCP timeout) || T084 (Gemini timeout)

**Phase 12 (Polish)**:
- T088 (logging) || T089 (metrics) || T090 (README) || T096 (cleanup) || T097 (docstrings)

**User Stories (after Foundation)**:
- US2 (T052-T060) || US3 (T061-T069) || US4 (T070-T080) can all run in parallel after US1 complete

---

## Parallel Example: Foundation Phase

```bash
# Phase 1: Environment & Boilerplate (Sequential start, then parallel)
T001 → T002 → T003 → T004
Then parallel:
  T005 (.env.example)
  T006 (.gitignore)
  T010 (Dockerfile)
  T011 (docker-compose.yml)

# Phase 6: Observability (Can start in parallel with Phase 2-5)
T037 → T038 → T039 → T040 → T041 → T042 → T043
```

---

## Parallel Example: User Story Implementation

```bash
# After Foundation (T001-T043) completes:
# Launch User Story 1 (MVP - MUST complete first):
T044 → T045 → T046 → T047 → T048 → T049 → T050 → T051

# After US1 completes, launch all remaining stories in parallel:
US2 (T052-T060) || US3 (T061-T069) || US4 (T070-T080)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Environment & Boilerplate (T001-T011)
2. Complete Phase 2: Gemini Bridge (T012-T016)
3. Complete Phase 3: MCP Client (T017-T021)
4. Complete Phase 4: ChatKit Streaming (T022-T029)
5. Complete Phase 5: Resilience (T030-T036)
6. Complete Phase 6: Observability (T037-T043)
7. Complete Phase 7: User Story 1 (T044-T051)
8. **STOP and VALIDATE**: Test create todo via /chat/stream independently
9. Deploy/demo if ready

### Incremental Delivery

1. Complete Phases 1-6 → Foundation ready (T001-T043)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - T044-T051)
3. Add User Story 2 → Test independently → Deploy/Demo (T052-T060)
4. Add User Story 3 → Test independently → Deploy/Demo (T061-T069)
5. Add User Story 4 → Test independently → Deploy/Demo (T070-T080)
6. Add Edge Cases → Test error scenarios → Deploy/Demo (T081-T087)
7. Polish and production hardening → Final release (T088-T097)

### Parallel Team Strategy

With multiple developers after Foundation (T001-T043) complete:

1. Team completes Phases 1-6 together (Foundation)
2. Once Foundation is done:
   - Developer A: User Story 1 (T044-T051) - **MUST complete first**
3. After US1 complete:
   - Developer A: User Story 2 (T052-T060)
   - Developer B: User Story 3 (T061-T069)
   - Developer C: User Story 4 (T070-T080)
4. After all stories complete:
   - Team collaborates on Edge Cases (T081-T087) and Polish (T088-T097)

---

## Summary

**Total Tasks**: 97
**Task Breakdown by Phase**:
- Phase 1 (Environment & Boilerplate): 11 tasks (T001-T011)
- Phase 2 (Gemini Bridge): 5 tasks (T012-T016)
- Phase 3 (MCP Client): 5 tasks (T017-T021)
- Phase 4 (ChatKit Streaming): 8 tasks (T022-T029)
- Phase 5 (Resilience): 7 tasks (T030-T036)
- Phase 6 (Observability): 7 tasks (T037-T043)
- Phase 7 (User Story 1 - Create): 8 tasks (T044-T051)
- Phase 8 (User Story 2 - Query): 9 tasks (T052-T060)
- Phase 9 (User Story 3 - Update): 9 tasks (T061-T069)
- Phase 10 (User Story 4 - Delete): 11 tasks (T070-T080)
- Phase 11 (Edge Cases): 7 tasks (T081-T087)
- Phase 12 (Polish): 10 tasks (T088-T097)

**Parallel Opportunities Identified**: 18 tasks marked [P] across all phases

**Independent Test Criteria**:
- US1: Send create request → verify MCP create_todo called with correct parameters
- US2: Send query request → verify MCP list_todos called with correct filters
- US3: Send update request → verify MCP update_todo called with correct parameters
- US4: Send single delete → verify immediate deletion | Send mass delete → verify confirmation request

**MVP Scope**: Phases 1-7 (T001-T051) - User Story 1 only
**Full Feature Scope**: All phases (T001-T097)

**Format Validation**: ✅ All tasks follow checklist format (checkbox, ID, optional [P], optional [Story], description with file path)
