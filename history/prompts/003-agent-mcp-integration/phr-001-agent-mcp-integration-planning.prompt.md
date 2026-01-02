---
id: phr-003-001
title: Agent MCP Integration Planning
stage: plan
date: 2025-12-31
surface: claude-code-cli
model: claude-sonnet-4-5
feature: 003-agent-mcp-integration
branch: 003-agent-mcp-integration
user: developer
command: /sp.plan
labels: [planning, mcp, agent-integration, architecture, research]
links:
  spec: specs/003-agent-mcp-integration/spec.md
  ticket: N/A
  adr: N/A
  pr: N/A
files:
  created:
    - specs/003-agent-mcp-integration/plan.md
    - specs/003-agent-mcp-integration/research.md
    - specs/003-agent-mcp-integration/data-model.md
    - specs/003-agent-mcp-integration/quickstart.md
    - specs/003-agent-mcp-integration/contracts/mcp-connection.json
    - specs/003-agent-mcp-integration/contracts/tool-registry.json
    - specs/003-agent-mcp-integration/contracts/chat-streaming.openapi.yaml
  modified:
    - CLAUDE.md (agent context updated with Python 3.11+ and PostgreSQL)
tests:
  plan:
    - Integration tests for MCP connection lifecycle
    - Integration tests for agent tool execution
    - Integration tests for ChatKit streaming events
    - Unit tests for degraded mode handling
---

## Prompt

Integrate the FastAPI Orchestrator with the FastMCP Database Server to create a fully functional AI-driven Todo application.

1. Connection Strategy:

Primary Transport: Use MCPServerStdio for development. The Orchestrator will spawn the FastMCP server as a managed subprocess using uv run.

Secondary Transport: Prepare an MCPServerSse configuration for production, connecting to the MCP server's URL.

2. Agentic Handshake:

Initialization: In the FastAPI lifespan, initialize the MCPServer instance and call .connect().

Dynamic Registration: Pass the connected mcp_server instance into the Agent(mcp_servers=[...]) constructor. This allows the agent to automatically inherit the create_todo, list_todos, etc., tools from the FastMCP server.

3. ChatKit Streaming Logic:

Implement an async generator to stream the Agent.run() output to the ChatKit endpoint.

Ensure the stream correctly captures and transmits "tool_use" and "tool_result" events so the user sees the agent interacting with the Neon database in real-time.

4. Constraints & Optimization:

Max Tasks: Keep the implementation roadmap to 15–18 tasks total.

Stateless Hand-off: Ensure the Orchestrator remains a "pure brain"—it should never touch the database directly, only through the MCP tools.

Environment: Use python-dotenv to share the DATABASE_URL and MCP_SERVER_PATH across the environment.

5. Verification:

Use the MCP Inspector to verify that the FastMCP server correctly exposes the JSON-RPC schema before finalizing the FastAPI bridge.

## Response snapshot

Generated comprehensive implementation plan for Agent-MCP integration with the following deliverables:

### Planning Artifacts Created

1. **plan.md** - Complete implementation plan with:
   - Summary and technical approach
   - Technical context (Python 3.11+, OpenAI Agents SDK 0.6.4+, FastMCP 2.14.0+, Gemini 2.5 Flash)
   - Constitution compliance check (all 6 principles PASS)
   - Project structure (single project layout)
   - Phase 0: Research findings (8 research topics resolved)
   - Phase 1: Design & contracts
   - Implementation strategy (17 tasks in 4 phases)
   - Appendices (MCP docs, env vars, testing strategy, rollout plan)

2. **research.md** - Detailed research findings:
   - MCP transport selection (MCPServerStdio chosen)
   - Dynamic tool discovery mechanism (via Agent mcp_servers parameter)
   - FastAPI lifespan management pattern
   - Timeout & retry configuration (5s timeout, 3 retries)
   - Graceful degraded mode design (HTTP 200 with friendly errors)
   - FastMCP server verification (MCP Inspector usage)
   - ChatKit SSE event mapping (existing implementation correct)
   - Localhost security enforcement (stdio transport inherent)

3. **data-model.md** - Entity definitions:
   - MCP Connection (runtime state with transport type, connection state)
   - Tool Registry (5 CRUD tools with schemas)
   - Tool Call Context (request-scoped metadata)
   - Circuit Breaker State (CLOSED/OPEN/HALF-OPEN)

4. **quickstart.md** - Complete setup guide:
   - Prerequisites (Python 3.11+, uv, PostgreSQL, Gemini API key)
   - 10-step tutorial (environment setup → testing degraded mode)
   - Troubleshooting section (4 common issues)
   - Next steps (ChatKit integration, production deployment)

5. **contracts/** - API contracts:
   - mcp-connection.json (JSON Schema for MCP connection state)
   - tool-registry.json (JSON Schema for 5 CRUD tools)
   - chat-streaming.openapi.yaml (OpenAPI 3.0 spec for SSE endpoint)

### Key Decisions

1. **Transport Protocol**: MCPServerStdio (stdio) for development, SSE prepared for production
2. **Timeout Configuration**: Reduced from 30s to 5s to align with FR-017
3. **Degraded Mode**: HTTP 200 with user-friendly errors (never 503 for todo operations)
4. **MCP Connection Lifecycle**: Shared instance in app.state initialized via FastAPI lifespan
5. **Security**: Stdio transport inherently localhost-only (no network binding)

### Constitution Compliance

All 6 principles verified:
- ✅ Environment-First Rule (uv exclusively, .venv activation documented)
- ✅ Source of Truth Protocol (Context7 MCP docs fetched for OpenAI Agents SDK and FastMCP)
- ✅ Pre-Flight Skills (spec.md → plan.md → tasks.md workflow)
- ✅ uv-Exclusive Package Management (no pip/poetry/conda)
- ✅ Model Architecture (Gemini 2.5 Flash via AsyncOpenAI bridge)
- ✅ Test-First Development (test requirements documented)

### Context7 Documentation Retrieved

1. **OpenAI Agents SDK** (/openai/openai-agents-python):
   - MCPServerStdio usage patterns
   - Dynamic tool discovery via mcp_servers parameter
   - Tool filtering (optional, not used)
   - Transport options (stdio, SSE, HTTP, Hosted)

2. **FastMCP** (/jlowin/fastmcp):
   - @mcp.tool decorator usage
   - Tool configuration (name, description, tags, metadata)
   - Parameter validation via JSON Schema
   - Server execution via stdin/stdout

### Implementation Strategy

**17 Tasks in 4 Phases** (within 15-18 target):

**Phase 1: MCP Connection Setup (5 tasks)**
- Update config timeout from 30s to 5s
- Enhance FastAPI lifespan for MCP initialization
- Store MCP server in app.state
- Add health check integration
- Implement degraded mode handling

**Phase 2: Agent Integration (4 tasks)**
- Use shared MCP connection from app.state
- Verify dynamic tool discovery
- Test all 5 CRUD operations
- Validate tool call context metadata

**Phase 3: Error Handling & Resilience (4 tasks)**
- Catch circuit breaker exceptions (HTTP 200 with friendly errors)
- Update health check for degraded mode (HTTP 200, not 503)
- Verify retry logic (3 attempts, exponential backoff)
- Test circuit breaker transitions

**Phase 4: Verification & Documentation (4 tasks)**
- Use MCP Inspector to verify schema
- End-to-end integration test
- Graceful degradation test
- Update quickstart.md

### Agent Context Update

Ran `update-agent-context.ps1` to add:
- Language: Python 3.11+
- Database: PostgreSQL with connection pooling (2 min, 8 max overflow)

Updated CLAUDE.md with project-specific technical context.

## Outcome

- ✅ Impact: Comprehensive implementation plan ready for /sp.tasks execution. All research completed, design artifacts created, contracts defined. Agent-MCP integration architecture fully specified with 17 actionable tasks.

- 🧪 Tests: Integration test strategy defined for 3 test files (test_mcp_connection.py, test_agent_tools.py, test_streaming.py). Target >80% coverage for new integration code. Pytest fixtures for MCP server lifecycle and degraded mode scenarios.

- 📁 Files: Created 7 new files (plan.md, research.md, data-model.md, quickstart.md, 3 contract files). Modified 1 file (CLAUDE.md with agent context). All files under specs/003-agent-mcp-integration/.

- 🔁 Next prompts:
  1. Execute /sp.tasks to generate detailed task breakdown from plan.md
  2. Begin implementation with Phase 1: MCP Connection Setup (5 tasks)
  3. Verify MCP server schema using MCP Inspector (Task 14)
  4. Run integration tests after implementation (Phase 4)

- 🧠 Reflection: Planning process followed SDD-RI methodology rigorously. Context7 MCP integration proved invaluable for getting current OpenAI Agents SDK and FastMCP patterns. Key insight: stdio transport inherently satisfies localhost security requirement (no network binding). Degraded mode design (HTTP 200 with friendly errors) aligns with spec SC-013 and improves UX over 503 errors. Task count (17) within target range (15-18) ensures rapid implementation.

## Evaluation notes (flywheel)

- Failure modes observed: None. PowerShell script execution required explicit path handling for Windows. Bash script for PHR creation not found, resolved by manual template-based creation.

- Graders run and results (PASS/FAIL):
  - Constitution Check: PASS (all 6 principles satisfied)
  - Context7 Documentation Fetched: PASS (2 libraries queried)
  - Task Count Target: PASS (17 tasks within 15-18 range)
  - Research Completeness: PASS (8 unknowns resolved)
  - Contract Validation: PASS (3 contract files with JSON Schema/OpenAPI)

- Prompt variant (if applicable): N/A (standard /sp.plan workflow)

- Next experiment (smallest change to try): For future planning sessions, consider adding Architecture Decision Record (ADR) creation for transport protocol selection (stdio vs SSE) to document rationale for posterity. Could improve onboarding for new developers joining the project.
