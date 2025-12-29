# Implementation Plan: AI Agent Orchestrator for Todo Management

**Branch**: `001-ai-agent-orchestrator` | **Date**: 2025-12-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-agent-orchestrator/spec.md` (with clarifications from 2025-12-21 session)

**Note**: This plan has been updated to incorporate 5 critical clarifications added to spec.md.

## Summary

Build a FastAPI-based orchestrator that converts natural language todo requests into structured MCP tool calls. The system uses OpenAI Agents SDK with AsyncOpenAI bridged to Google Gemini 2.5 Flash, providing ChatKit-compatible streaming responses. The orchestrator remains stateless, delegating all data persistence to an external FastMCP server handling PostgreSQL operations.

**New from Clarifications**: The system implements structured JSON logging, exponential backoff with circuit breaker for external dependencies, input validation/sanitization, runs on Python 3.11+ in Docker containers, and targets 99% uptime SLO with graceful degradation.

## Technical Context

**Language/Version**: Python 3.11+ (clarified: required for performance and long-term support)

**Primary Dependencies**:
- FastAPI (async web framework)
- OpenAI Agents SDK with AsyncOpenAI (agentic orchestration)
- agents_mcp (MCP integration for external FastMCP server)
- Pydantic (data validation and input sanitization)
- structlog or python-json-logger (structured JSON logging - NEW)
- tenacity (exponential backoff retry logic - NEW)
- pybreaker or circuitbreaker (circuit breaker pattern - NEW)

**Storage**: N/A (stateless orchestrator - all persistence delegated to external MCP server with PostgreSQL/SQLModel)

**Testing**: pytest with async support (pytest-asyncio), httpx for endpoint testing, pytest-timeout for circuit breaker tests

**Target Platform**: Docker containerized deployment on Linux/Windows (clarified: Docker required for consistent environments and horizontal scaling)

**Project Type**: Single backend service (API server)

**Performance Goals**:
- <2 seconds from request to first streaming token (excluding MCP tool execution)
- Handle 100+ concurrent streaming connections
- **NEW**: 99% uptime SLO (max 3.6 days downtime/year)

**Constraints**:
- Stateless architecture (no local state storage)
- All CRUD operations must go through MCP tools
- Streaming responses must support ChatKit protocol (Thinking blocks + Tool Calls)
- Async I/O throughout (FastAPI, MCP client, Gemini calls)
- **NEW**: Maximum 5000 character input limit with UTF-8 validation and control character stripping
- **NEW**: Must implement circuit breaker to prevent cascading failures

**Scale/Scope**:
- Single-user conversational interface (no multi-tenancy in MVP)
- 4 core user stories (Create, Read, Update, Delete todos via natural language)
- Target: 100 concurrent users without degradation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Environment-First Rule ✅
- **Status**: PASS
- **Evidence**: Planning phase - will verify `.venv` activation before any `uv` commands in implementation
- **Action**: Document environment activation in quickstart.md (includes Docker setup now)

### Source of Truth Protocol (MCP) ✅
- **Status**: COMPLETE (from first planning pass)
- **MCP Documentation Fetched**:
  1. FastAPI (routing, async endpoints, SSE streaming)
  2. OpenAI Agents SDK (agent initialization, tool creation, AsyncOpenAI with custom base_url)
  3. agents_mcp (MCP integration, tool discovery, async invocation)
  4. **NEW REQUIRED**: Research circuit breaker libraries (pybreaker, tenacity)
  5. **NEW REQUIRED**: Research structured logging libraries (structlog, python-json-logger)

### Pre-Flight Skills Requirement ✅
- **Status**: PASS
- **Evidence**: Currently executing `/sp.plan` skill (second pass with clarifications)
- **Next**: `/sp.tasks` will be executed after plan completion
- **Workflow**: `/sp.specify` (done) → `/sp.clarify` (done) → `/sp.plan` (in progress - 2nd pass) → `/sp.tasks` (next)

### uv-Exclusive Package Management ✅
- **Status**: PASS (by design)
- **Evidence**: All dependency management will use `uv pip install`, `uv run`
- **Action**: Document uv commands in quickstart.md and research.md

### Model & Connectivity Architecture ✅
- **Status**: RESOLVED (from first planning pass)
- **Required**: AsyncOpenAI initialization with Gemini bridge
- **Model Target**: gemini-2.5-flash
- **Configuration**: base_url for Gemini endpoint, set_default_openai_client()

### Test-First Development ✅
- **Status**: PASS (by design)
- **Evidence**: Spec includes acceptance scenarios for all 4 user stories + 9 success criteria (including new SC-009 for uptime)
- **NEW Testing Requirements**:
  - Circuit breaker behavior tests (verify threshold triggers)
  - Structured logging validation (verify JSON format, request IDs)
  - Input validation tests (5000 char limit, control char stripping, UTF-8)
  - Uptime monitoring simulation tests

### Stateless Architecture ✅
- **Status**: PASS
- **Evidence**: Spec explicitly requires stateless orchestrator with all persistence delegated to MCP server
- **No Violations**: No local database, no session storage, no state management
- **Validation**: Architecture enforces separation of concerns (orchestration vs. persistence)

### Summary
**Post-Clarification Status**: All gates PASS
**New Requirements**: 3 additional functional requirements (FR-011, FR-012, FR-013) and 1 new success criterion (SC-009)
**Proceed to Phase 0**: Update research.md with new requirements

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-agent-orchestrator/
├── spec.md              # Feature specification with clarifications
├── plan.md              # This file (/sp.plan command output - UPDATED)
├── research.md          # Phase 0 output - TO BE UPDATED
├── data-model.md        # Phase 1 output - TO BE UPDATED
├── quickstart.md        # Phase 1 output - TO BE UPDATED
├── contracts/           # Phase 1 output - TO BE UPDATED
│   ├── openapi.yaml
│   └── mcp-tools.md
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── main.py                    # FastAPI application entry point
├── config.py                  # Environment configuration (Gemini API, MCP server)
├── agents/
│   ├── __init__.py
│   ├── todo_agent.py          # OpenAI Agents SDK agent with MCP tools
│   └── tool_definitions.py    # MCP tool schemas for agent
├── api/
│   ├── __init__.py
│   ├── routes.py              # ChatKit streaming endpoint
│   ├── schemas.py             # Pydantic request/response models
│   └── validation.py          # NEW: Input validation and sanitization
├── mcp/
│   ├── __init__.py
│   └── client.py              # MCP integration (agents_mcp)
├── streaming/
│   ├── __init__.py
│   └── chatkit.py             # openai-chatkit streaming implementation
├── observability/             # NEW: Logging and monitoring
│   ├── __init__.py
│   ├── logging.py             # Structured JSON logging setup
│   └── metrics.py             # Performance metrics tracking
└── resilience/                # NEW: Failure handling
    ├── __init__.py
    ├── circuit_breaker.py     # Circuit breaker implementation
    └── retry.py               # Exponential backoff retry logic

tests/
├── contract/
│   └── test_chatkit_endpoint.py   # ChatKit protocol compliance
├── integration/
│   ├── test_mcp_tools.py          # MCP tool invocation tests
│   ├── test_agent_flows.py        # Agent reasoning + tool execution
│   └── test_circuit_breaker.py    # NEW: Circuit breaker behavior
└── unit/
    ├── test_intent_extraction.py  # Natural language parsing
    ├── test_config.py              # Configuration validation
    ├── test_validation.py          # NEW: Input validation tests
    └── test_logging.py             # NEW: Structured logging tests

.env.example                   # Template for API keys and MCP server config
pyproject.toml                 # uv dependencies (updated with new libs)
Dockerfile                     # NEW: Docker containerization
docker-compose.yml             # NEW: Local development stack
```

**Structure Decision**: Single backend service with new modules for observability and resilience. Docker containerization added per clarifications.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No Constitution Violations** - This plan complies with all constitutional requirements:
- Environment-First: Documented in quickstart.md (Docker-aware)
- MCP Documentation: Fetched via Context7 (see research.md)
- uv-Exclusive: All dependency commands use `uv`
- Gemini Model: AsyncOpenAI configured with custom base_url
- Test-First: Acceptance criteria defined in spec.md (9 success criteria)
- Stateless Architecture: No local persistence

---

## Phase 0 Update: New Research Requirements

### Additional Research Tasks (from Clarifications)

1. **Circuit Breaker Libraries**
   - Research: pybreaker vs circuitbreaker vs tenacity
   - Evaluate: Async support, threshold configuration, monitoring hooks
   - Decision criteria: FastAPI compatibility, ease of testing

2. **Structured Logging**
   - Research: structlog vs python-json-logger
   - Evaluate: Request ID correlation, performance overhead, integration with FastAPI
   - Decision criteria: JSON output format, async logging support

3. **Input Validation Patterns**
   - Research: Pydantic validation for control characters and UTF-8
   - Evaluate: Custom validators vs built-in validators
   - Decision criteria: Performance, maintainability

4. **Docker Best Practices for FastAPI**
   - Research: Multi-stage builds, non-root user, health checks
   - Evaluate: Image size optimization, security scanning
   - Decision criteria: Production readiness, CI/CD integration

### research.md Update Required

Add new decision sections:
- **Decision 5**: Circuit Breaker Library Selection
- **Decision 6**: Structured Logging Framework
- **Decision 7**: Docker Base Image and Configuration

---

## Phase 1 Update: New Design Requirements

### data-model.md Updates

1. **Input Validation Schema** (NEW):
   - ChatRequest validation rules
   - Control character filtering logic
   - UTF-8 encoding validation

2. **Logging Event Schema** (NEW):
   - Log entry structure (JSON format)
   - Request ID generation and propagation
   - Timing metrics capture points

3. **Circuit Breaker State** (NEW):
   - State transitions (closed → open → half-open)
   - Failure threshold configuration
   - Recovery timeout settings

### contracts/openapi.yaml Updates

1. Add `/health` endpoint with detailed status:
   - Circuit breaker states (MCP, Gemini)
   - Uptime metrics
   - Request rate statistics

2. Update error responses:
   - 503 Service Unavailable (circuit breaker open)
   - 429 Too Many Requests (rate limiting - future)

### quickstart.md Updates

1. **Docker Setup Section** (NEW):
   - Docker installation verification
   - Building the container image
   - Running with docker-compose
   - Environment variable configuration in Docker

2. **Logging Verification** (NEW):
   - Checking structured logs
   - Request ID tracing
   - Log aggregation setup (optional)

3. **Circuit Breaker Testing** (NEW):
   - Simulating MCP server failures
   - Verifying circuit breaker triggers
   - Testing graceful degradation

---

## Implementation Roadmap (Updated for /sp.tasks)

After this planning update, the `/sp.tasks` command will generate tasks.md with:

### 1. Setup Tasks
- Environment, dependencies, MCP configuration
- **NEW**: Docker configuration and multi-stage build
- **NEW**: Structured logging setup

### 2. Core Agent Tasks
- Agent initialization, Gemini client setup, tool discovery
- (No major changes from first plan)

### 3. API Tasks
- FastAPI endpoints, SSE streaming, Pydantic schemas
- **NEW**: Input validation middleware
- **NEW**: Request ID middleware for logging

### 4. Resilience Tasks (NEW)
- Circuit breaker implementation for MCP client
- Circuit breaker implementation for Gemini client
- Exponential backoff retry logic
- Graceful degradation error messages

### 5. Observability Tasks (NEW)
- Structured JSON logging configuration
- Request ID generation and propagation
- Timing metrics instrumentation
- Health check endpoint with circuit breaker status

### 6. Testing Tasks
- Contract, integration, and unit tests for all user stories
- **NEW**: Circuit breaker behavior tests
- **NEW**: Input validation tests
- **NEW**: Logging format tests
- **NEW**: Uptime SLO simulation tests

**Estimated Task Count**: 25-30 tasks (increased from 15-20 due to clarifications)

---

## Architecture Decision Records (ADR) Suggestions

Based on clarifications, **3 new ADR candidates** identified:

### Suggested ADR 3: Circuit Breaker Pattern for External Dependencies
**Decision**: Implement circuit breaker pattern with exponential backoff for MCP server and Gemini API
**Impact**: Long-term (affects all external service integrations, failure recovery strategy)
**Alternatives**: Simple retries, fail-fast, manual fallback
**Scope**: Cross-cutting (affects error handling, monitoring, SLO compliance)

**Suggestion**: 📋 Architectural decision detected: Circuit breaker pattern for resilience - Document reasoning and tradeoffs? Run `/sp.adr circuit-breaker-resilience`

### Suggested ADR 4: Structured Logging with Request Correlation
**Decision**: Implement structured JSON logging with request IDs for observability
**Impact**: Long-term (affects debugging, monitoring, operational support)
**Alternatives**: Plain text logs, minimal logging, verbose logging
**Scope**: Cross-cutting (affects all request handlers, error paths, tool executions)

**Suggestion**: 📋 Architectural decision detected: Observability strategy - Document reasoning and tradeoffs? Run `/sp.adr observability-logging-strategy`

### Suggested ADR 5: Docker Containerization for Deployment
**Decision**: Use Docker containers for consistent deployment across environments
**Impact**: Long-term (affects deployment pipeline, scaling strategy, environment management)
**Alternatives**: Direct VM deployment, serverless functions, bare metal
**Scope**: Cross-cutting (affects build process, CI/CD, production operations)

**Suggestion**: 📋 Architectural decision detected: Deployment containerization - Document reasoning and tradeoffs? Run `/sp.adr docker-deployment-strategy`

### Previous ADRs (from first plan):
- ADR 1: MCP Integration Strategy (agents_mcp vs raw SDK)
- ADR 2: Gemini Model Integration (AsyncOpenAI bridge)

---

## Risks and Mitigation (Updated)

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ChatKit protocol specification unclear | High | Medium | Create minimal viable SSE format; iterate with frontend team |
| MCP server latency affects UX | Medium | High | Implement streaming status updates; set 30s timeout; circuit breaker prevents cascade |
| Gemini API rate limits | Medium | Low | Exponential backoff retry logic; circuit breaker; monitor usage |
| agents_mcp compatibility issues | High | Low | Pin dependency versions; test with multiple MCP servers |
| SSE connection drops mid-stream | Medium | Medium | Implement connection health checks; graceful error messages |
| **NEW**: Circuit breaker false positives | Medium | Medium | Tune failure threshold and timeout; implement half-open state testing; monitoring alerts |
| **NEW**: Docker image size bloat | Low | High | Multi-stage builds; minimize dependencies; use slim base images |
| **NEW**: Logging performance overhead | Low | Low | Async logging; structured format overhead is minimal; monitor log volume |
| **NEW**: 99% uptime SLO challenging with single instance | Medium | Medium | Docker enables horizontal scaling; circuit breaker prevents cascade; health checks enable auto-restart |

---

## Next Steps

1. **Update research.md** with circuit breaker, logging, and Docker research
2. **Update data-model.md** with validation schemas, logging events, circuit breaker state
3. **Update contracts/openapi.yaml** with /health endpoint and new error codes
4. **Update quickstart.md** with Docker setup and testing procedures
5. **Execute `/sp.tasks`** to generate detailed task breakdown incorporating all clarifications
6. **Optionally create ADRs** for circuit breaker, logging, and Docker decisions
7. **Begin implementation** following tasks.md order

---

## Changelog (Plan Revisions)

### Revision 2 (2025-12-21)
**Reason**: Incorporated 5 clarifications from `/sp.clarify` session

**Changes**:
- Updated Technical Context with Python 3.11+, Docker, new dependencies
- Added 3 new functional requirements (FR-011, FR-012, FR-013)
- Added 1 new success criterion (SC-009: 99% uptime SLO)
- Expanded project structure with observability/ and resilience/ modules
- Added Phase 0 research tasks for circuit breaker, logging, Docker
- Added Phase 1 design updates for validation, logging, health checks
- Increased task estimate from 15-20 to 25-30
- Added 3 new ADR suggestions
- Updated risk analysis with 4 new risks

### Revision 1 (2025-12-21)
**Reason**: Initial planning pass from PLAN_PROMPT.md and original spec.md
