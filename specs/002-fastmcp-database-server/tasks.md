# Tasks: FastMCP Database Server for Todo Management

**Input**: Design documents from `/specs/002-fastmcp-database-server/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete), contracts/ (complete)

**Tests**: Tests are included per the research.md testing strategy (>80% coverage target)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/mcp_server/`, `tests/mcp_server/` at repository root
- All paths are absolute from repository root: `D:\hackathonII-Backend\`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic MCP server structure

- [x] T001 Create MCP server directory structure at src/mcp_server/ with subdirectories: tools/, and __init__.py files
- [x] T002 Create test directory structure at tests/mcp_server/ with __init__.py
- [x] T003 [P] Update .env.example with DATABASE_URL template using postgresql:// protocol (psycopg2 format) and sslmode=require
- [x] T004 [P] Install dependencies via uv: fastmcp, sqlmodel, psycopg2-binary, python-dotenv, pytest

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core database infrastructure and MCP server framework that MUST be complete before ANY user story tools can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement TodoStatus enum and Todo SQLModel entity in src/mcp_server/models.py with all 6 fields (id, title, description, status, created_at, updated_at)
- [x] T006 [P] Implement database engine creation with connection pooling in src/mcp_server/database.py using create_engine with pool_size=2, max_overflow=8, pool_pre_ping=True, pool_recycle=3600
- [x] T007 [P] Implement session factory and get_session dependency in src/mcp_server/database.py using Session with context manager
- [x] T008 Implement create_db_and_tables function in src/mcp_server/database.py using SQLModel.metadata.create_all (synchronous)
- [x] T009 [P] Implement Pydantic validation schemas in src/mcp_server/schemas.py: CreateTodoInput, UpdateTodoInput with field validators
- [x] T010 Create FastMCP server instance in src/mcp_server/server.py including database initialization on startup
- [x] T011 [P] Setup pytest fixtures in tests/mcp_server/conftest.py for test database session using sqlite:///:memory:

**Checkpoint**: Foundation ready - user story tool implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Todo Creation and Retrieval (Priority: P1) 🎯 MVP

**Goal**: Enable AI agent to create new todos and retrieve active tasks - the minimum viable functionality for todo management

**Independent Test**: Create a todo via create_todo tool, then verify it appears in list_todos results. Success means both operations complete and data persists.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1] Write unit test for Todo model CRUD in tests/mcp_server/test_models.py testing create, read operations
- [X] T013 [P] [US1] Write integration test for create_todo tool in tests/mcp_server/test_tools.py verifying tool creates todo and returns correct MCP response format
- [X] T014 [P] [US1] Write integration test for list_todos tool in tests/mcp_server/test_tools.py verifying tool retrieves only active todos

### Implementation for User Story 1

- [X] T015 [US1] Implement create_todo tool in src/mcp_server/tools/create_todo.py using @mcp.tool decorator with session-per-tool pattern and CreateTodoInput validation
- [X] T016 [US1] Implement list_todos tool in src/mcp_server/tools/list_todos.py using @mcp.tool decorator with Session context manager, filtering by TodoStatus.ACTIVE
- [X] T017 [US1] Register create_todo and list_todos tools in src/mcp_server/server.py by importing and ensuring they use the shared mcp instance
- [X] T018 [US1] Add error handling for database integrity errors in create_todo tool (catch IntegrityError, raise ValueError with descriptive message)
- [X] T019 [US1] Verify contract compliance for create_todo against specs/002-fastmcp-database-server/contracts/create_todo.json
- [X] T020 [US1] Verify contract compliance for list_todos against specs/002-fastmcp-database-server/contracts/list_todos.json

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. AI agent can create and list todos.

---

## Phase 4: User Story 2 - Todo Modification and Status Updates (Priority: P2)

**Goal**: Enable AI agent to update existing todos (title, description, status changes) to maintain accurate task information

**Independent Test**: Create a todo (using P1 tools), call update_todo to change title and status to "completed", then verify changes persist and todo no longer appears in list_todos.

### Tests for User Story 2

- [ ] T021 [P] [US2] Write unit test for Todo model update operations in tests/mcp_server/test_models.py testing title, description, status updates and updated_at auto-update
- [ ] T022 [P] [US2] Write integration test for update_todo tool in tests/mcp_server/test_tools.py verifying partial updates, status transitions, and "not found" error handling
- [ ] T023 [P] [US2] Write integration test for soft delete behavior in tests/mcp_server/test_tools.py verifying completed todos excluded from list_todos

### Implementation for User Story 2

- [ ] T024 [US2] Implement update_todo tool in src/mcp_server/tools/update_todo.py using @mcp.tool decorator with UpdateTodoInput for partial updates
- [ ] T025 [US2] Add logic to manually update updated_at timestamp in update_todo tool (set to datetime.now(timezone.utc) on every update)
- [ ] T026 [US2] Implement "not found" error handling in update_todo tool (raise ValueError if todo ID doesn't exist)
- [ ] T027 [US2] Register update_todo tool in src/mcp_server/server.py
- [ ] T028 [US2] Verify contract compliance for update_todo against specs/002-fastmcp-database-server/contracts/update_todo.json
- [ ] T029 [US2] Add integration test verifying state transitions (active → completed → active) work correctly

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. AI agent can create, list, and update todos.

---

## Phase 5: User Story 3 - Todo Search and Discovery (Priority: P3)

**Goal**: Enable AI agent to find specific todos based on keywords without reviewing the entire list

**Independent Test**: Create multiple todos with different titles/descriptions, call search_todos with various keywords, verify only matching active todos are returned.

### Tests for User Story 3

- [ ] T030 [P] [US3] Write integration test for search_todos tool in tests/mcp_server/test_tools.py testing keyword matching in title
- [ ] T031 [P] [US3] Write integration test for search_todos tool in tests/mcp_server/test_tools.py testing keyword matching in description
- [ ] T032 [P] [US3] Write integration test for search_todos tool in tests/mcp_server/test_tools.py verifying completed/archived todos excluded from results
- [ ] T033 [P] [US3] Write integration test for search_todos tool in tests/mcp_server/test_tools.py testing case-insensitive search and empty results

### Implementation for User Story 3

- [ ] T034 [US3] Implement search_todos tool in src/mcp_server/tools/search_todos.py using ILIKE pattern matching on title and description fields
- [ ] T035 [US3] Add filtering logic to search_todos to only return active todos (exclude completed and archived statuses)
- [ ] T036 [US3] Implement case-insensitive search using SQLAlchemy .ilike() method in search_todos tool
- [ ] T037 [US3] Register search_todos tool in src/mcp_server/server.py
- [ ] T038 [US3] Verify contract compliance for search_todos against specs/002-fastmcp-database-server/contracts/search_todos.json

**Checkpoint**: All user stories 1, 2, and 3 should now be independently functional. AI agent has full search capabilities.

---

## Phase 6: User Story 4 - Safe Todo Deletion (Priority: P4)

**Goal**: Enable AI agent to permanently remove unwanted todos (hard delete) with proper error handling

**Independent Test**: Create a todo, call delete_todo with its ID, verify it no longer appears in list_todos and get_by_id returns "not found".

### Tests for User Story 4

- [ ] T039 [P] [US4] Write unit test for Todo model delete operation in tests/mcp_server/test_models.py
- [ ] T040 [P] [US4] Write integration test for delete_todo tool in tests/mcp_server/test_tools.py verifying permanent deletion
- [ ] T041 [P] [US4] Write integration test for delete_todo tool in tests/mcp_server/test_tools.py testing "not found" error for non-existent ID
- [ ] T042 [P] [US4] Write integration test for delete_todo tool in tests/mcp_server/test_tools.py verifying other todos remain unchanged after deletion

### Implementation for User Story 4

- [ ] T043 [US4] Implement delete_todo tool in src/mcp_server/tools/delete_todo.py using hard delete (session.delete) with error handling for non-existent IDs
- [ ] T044 [US4] Add "not found" error handling in delete_todo tool (raise ValueError if todo ID doesn't exist before attempting delete)
- [ ] T045 [US4] Register delete_todo tool in src/mcp_server/server.py
- [ ] T046 [US4] Verify contract compliance for delete_todo against specs/002-fastmcp-database-server/contracts/delete_todo.json

**Checkpoint**: All 4 user stories are complete. Full CRUD functionality available to AI agent.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and overall server quality

- [ ] T047 [P] Add comprehensive docstrings to all tools in src/mcp_server/tools/ following MCP description format
- [ ] T048 [P] Add logging statements to database operations in src/mcp_server/database.py for startup, table creation, and errors
- [ ] T049 [P] Create integration test in tests/mcp_server/test_database.py verifying database initialization and connection pooling
- [ ] T050 Run full test suite with coverage: uv run pytest tests/mcp_server/ --cov=src/mcp_server --cov-report=term-missing and verify >80% coverage
- [ ] T051 [P] Add input sanitization validation to prevent SQL injection in search_todos keyword parameter
- [ ] T052 Test server startup using quickstart.md instructions and verify all 5 tools are registered
- [ ] T053 [P] Add main() function and __main__ block to src/mcp_server/server.py for direct execution
- [ ] T054 Test MCP server with MCP Inspector to verify all tools work via stdio protocol
- [ ] T055 [P] Update pyproject.toml with all production dependencies (fastmcp, sqlmodel, psycopg2-binary, python-dotenv) and dev dependencies (pytest)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 but uses same models
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2 but uses same models
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Independent of US1/US2/US3 but uses same models

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Tool implementation depends on Pydantic schemas (from Phase 2)
- Tool registration depends on tool implementation
- Contract verification depends on tool implementation
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 (Setup)**: T003 and T004 can run in parallel
- **Phase 2 (Foundational)**: T006, T007, T009, T011 can run in parallel (different files)
- **User Story Tests**: All tests within a story marked [P] can run in parallel
- **Once Foundational completes**: All 4 user stories can start in parallel (if team capacity allows)
- **Phase 7 (Polish)**: T047, T048, T049, T051, T053, T055 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T012: "Write unit test for Todo model CRUD in tests/mcp_server/test_models.py"
Task T013: "Write integration test for create_todo tool in tests/mcp_server/test_tools.py"
Task T014: "Write integration test for list_todos tool in tests/mcp_server/test_tools.py"
```

---

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task T030: "Write integration test for search_todos - title matching"
Task T031: "Write integration test for search_todos - description matching"
Task T032: "Write integration test for search_todos - status filtering"
Task T033: "Write integration test for search_todos - case-insensitive and empty results"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T011) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T012-T020)
4. **STOP and VALIDATE**: Test User Story 1 independently using MCP Inspector
5. Deploy/demo if ready (create and list todos functionality)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T011)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! - create + list)
3. Add User Story 2 → Test independently → Deploy/Demo (+ update capabilities)
4. Add User Story 3 → Test independently → Deploy/Demo (+ search capabilities)
5. Add User Story 4 → Test independently → Deploy/Demo (+ delete capabilities)
6. Complete Polish → Production-ready MCP database server

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T011)
2. Once Foundational is done:
   - Developer A: User Story 1 (T012-T020)
   - Developer B: User Story 2 (T021-T029)
   - Developer C: User Story 3 (T030-T038)
   - Developer D: User Story 4 (T039-T046)
3. Stories complete and integrate independently
4. Team reconvenes for Polish phase (T047-T055)

---

## Task Count Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 7 tasks (BLOCKING)
- **Phase 3 (User Story 1 - P1)**: 9 tasks (MVP)
- **Phase 4 (User Story 2 - P2)**: 9 tasks
- **Phase 5 (User Story 3 - P3)**: 9 tasks
- **Phase 6 (User Story 4 - P4)**: 8 tasks
- **Phase 7 (Polish)**: 9 tasks

**Total Tasks**: 55 tasks

**Parallel Opportunities**: 23 tasks marked [P] can run in parallel when dependencies are met

---

## Notes

- [P] tasks = different files, no dependencies within their phase
- [US#] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail (RED) before implementing (GREEN)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All database operations use synchronous psycopg2 driver with thread-safe connection pooling
- All tools MUST return MCP-compliant Content objects (handled automatically by FastMCP)
- Connection string MUST use `postgresql://` protocol (psycopg2 format) with `?sslmode=require`

---

## Acceptance Criteria

**Per Task**:
- Every tool must return a descriptive string or JSON for the AI Agent to consume ✅
- All database operations use synchronous psycopg2 with thread-safe connection pooling ✅

**Overall**:
- All 5 MCP tools (create, list, update, delete, search) registered and functional
- Database initialization works with PostgreSQL (Neon or local) using psycopg2
- Test coverage >80% for business logic
- All contracts verified against JSON schemas in contracts/ directory
- Server runs in stdio mode and responds to MCP client tool invocations
- Connection pooling configured (min=2, max=10 connections)

---

## Next Steps

After tasks.md generation:

1. **Execute**: Run `/sp.implement` to begin task execution
2. **Validate**: After each user story phase, test independently using MCP Inspector
3. **Iterate**: Fix any failing tests before moving to next phase
4. **Document**: Create PHR for task generation process

**Command to Continue**: `/sp.implement` (executes tasks in dependency order)
