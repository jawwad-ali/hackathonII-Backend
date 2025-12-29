---
id: 002
title: AI Agent Orchestrator Implementation Plan
stage: plan
date: 2025-12-21
surface: agent
model: claude-sonnet-4.5
feature: 001-ai-agent-orchestrator
branch: 001-ai-agent-orchestrator
user: developer
command: /sp.plan
labels: ["planning", "architecture", "mcp", "agents-sdk", "fastapi", "gemini"]
links:
  spec: specs/001-ai-agent-orchestrator/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-ai-agent-orchestrator/plan.md
 - specs/001-ai-agent-orchestrator/research.md
 - specs/001-ai-agent-orchestrator/data-model.md
 - specs/001-ai-agent-orchestrator/contracts/openapi.yaml
 - specs/001-ai-agent-orchestrator/contracts/mcp-tools.md
 - specs/001-ai-agent-orchestrator/quickstart.md
tests:
 - N/A (Planning phase - no code written yet)
---

## Prompt

Read PLAN_PROMPT.md to generate plan.md

Initial request from PLAN_PROMPT.md:
```
Implement the FastAPI Orchestrator using a modular 3-server architecture.

1. Core Tech Stack:
Backend Framework: FastAPI (Async).
AI Engine: OpenAI Agents SDK using AsyncOpenAI to bridge with Google Gemini 2.5 Flash.
Package Manager: uv (strictly).

2. Architecture Rules:
Stateless Brain: The FastAPI server must remain stateless regarding the database.
MCP Integration: The TodoAgent must be configured to connect to an external FastMCP server (Server 3) using the official MCP Python SDK to perform all CRUD operations.
ChatKit Stream: Use the openai-chatkit Python library to expose a streaming endpoint that supports "Thinking" blocks and "Tool Calls" for the Next.js frontend.

3. Technical Mandates:
Ensure all I/O is asynchronous (FastAPI, MCP calls, Gemini streaming).
Cross-reference SKILLS/SKILL.md for standardized agent behavior.
Call context-7 MCP to verify the exact initialization syntax for the openai-agents SDK to ensure the Gemini bridge is correctly implemented.

4. Constraints:
No direct Postgres/SQLModel code in this server; it must only exist in the MCP server.
No custom session/threading logic; rely on the ChatKit protocol for thread management.
```

User clarifications during execution:
- Corrected library search: Use "openai-agents-python" instead of generic "openai python"
- Requested use of Context7 MCP for documentation fetching
- Provided OpenAI Agents SDK documentation URL: https://openai.github.io/openai-agents-python/

## Response snapshot

Successfully completed comprehensive implementation planning for AI Agent Orchestrator:

### Phase 0: Research (COMPLETE)
Fetched MCP documentation for:
- OpenAI Agents SDK (/websites/openai_github_io_openai-agents-python)
- agents_mcp extension (/lastmile-ai/openai-agents-mcp)
- FastAPI streaming (/fastapi/fastapi)

Key technical decisions documented in research.md:
1. Use agents_mcp extension for MCP integration (not raw SDK)
2. Configure AsyncOpenAI with custom base_url for Gemini bridge
3. Use FastAPI StreamingResponse for SSE
4. ChatKit protocol mapping deferred (needs specification)

### Phase 1: Design & Contracts (COMPLETE)
Created comprehensive design artifacts:
- **data-model.md**: Entities, validation rules, data flow (ChatRequest, StreamEvent, MCPToolCall, AgentContext, TodoAttributes)
- **contracts/openapi.yaml**: Full OpenAPI 3.1 spec with streaming endpoint, SSE event schemas
- **contracts/mcp-tools.md**: MCP tool interface contracts (create_todo, list_todos, update_todo, delete_todo)
- **quickstart.md**: Developer setup guide with environment, configuration, testing

### Architecture Highlights:
- **Stateless orchestrator**: No local persistence, all data in external MCP server
- **Streaming SSE**: ChatKit-compatible events (thinking, tool_call, response_delta, error, done)
- **MCP Tool Discovery**: Dynamic discovery via agents_mcp configuration
- **Async Throughout**: FastAPI, AsyncOpenAI (Gemini), MCP calls all async

### Constitution Compliance:
✅ Environment-First: Documented in quickstart.md
✅ MCP Documentation: Fetched via Context7
✅ uv-Exclusive: All commands use uv
✅ Gemini Model: AsyncOpenAI with custom base_url
✅ Test-First: Acceptance scenarios in spec.md
✅ Stateless: No local database/session storage

### ADR Suggestions:
- MCP integration strategy (agents_mcp vs raw SDK)
- Gemini model integration (AsyncOpenAI bridge)

## Outcome

- ✅ Impact: Comprehensive implementation plan with research, design, contracts, and quickstart guide. All constitution gates PASS. Ready for /sp.tasks.
- 🧪 Tests: No tests written (planning phase). Test strategy defined in spec.md acceptance scenarios.
- 📁 Files: 6 artifacts created (plan.md, research.md, data-model.md, openapi.yaml, mcp-tools.md, quickstart.md)
- 🔁 Next prompts: Execute /sp.tasks to generate task breakdown, optionally create ADRs (/sp.adr), begin implementation
- 🧠 Reflection: MCP documentation fetching via Context7 was highly effective. ChatKit protocol specification remains unclear but deferred appropriately. agents_mcp discovery simplified MCP integration significantly compared to raw SDK approach.

## Evaluation notes (flywheel)

- Failure modes observed: Initial incorrect library search ("openai python" vs "openai-agents-python"), resolved with user correction. ChatKit protocol details unavailable but properly flagged as NEEDS CLARIFICATION.
- Graders run and results (PASS/FAIL): N/A (planning phase, no code to grade)
- Prompt variant (if applicable): Standard /sp.plan workflow with MCP documentation fetching
- Next experiment (smallest change to try): Implement minimal ChatKit SSE event format and iterate with frontend feedback
