# Research & Technology Decisions: AI Agent Orchestrator

**Feature**: 001-ai-agent-orchestrator
**Date**: 2025-12-21
**Phase**: 0 (Research)

This document consolidates all technology research findings to resolve NEEDS CLARIFICATION items from plan.md Technical Context.

## Research Tasks

### 1. OpenAI Agents SDK - Gemini Bridge Configuration
**Question**: How to initialize AsyncOpenAI with Google Gemini as the model provider?

**Research Method**: Fetched OpenAI Agents SDK documentation via context-7 MCP (/websites/openai_github_io_openai-agents-python)

**Status**: RESOLVED

**Findings**:
- **Custom Client Configuration**: Use `set_default_openai_client()` to configure AsyncOpenAI with custom base_url
  ```python
  from openai import AsyncOpenAI
  from agents import set_default_openai_client

  custom_client = AsyncOpenAI(base_url="...", api_key="...")
  set_default_openai_client(custom_client)
  ```
- **Agent Initialization**: Standard Agent class with tools and instructions
  ```python
  from agents import Agent, Runner

  agent = Agent(
      name="Assistant",
      instructions="...",
      tools=[...]
  )
  ```
- **Async Execution**: Use `Runner.run()` for single execution, `Runner.run_streamed()` for streaming
- **Tool Definition**: Use `@function_tool` decorator for custom tools

---

### 2. MCP Integration with OpenAI Agents SDK
**Question**: How to integrate MCP servers with OpenAI Agents SDK?

**Research Method**: Fetched openai-agents-mcp documentation via context-7 MCP (/lastmile-ai/openai-agents-mcp)

**Status**: RESOLVED

**Findings**:
- **Package**: Use `agents_mcp` (extension of openai-agents SDK)
- **Agent Initialization with MCP**:
  ```python
  from agents_mcp import Agent, RunnerContext

  agent = Agent(
      name="MCP Assistant",
      instructions="...",
      tools=[local_tools],  # Regular tools
      mcp_servers=["fetch", "filesystem"]  # MCP server names from config
  )
  ```
- **Configuration File**: `mcp_agent.config.yaml` defines MCP servers
  ```yaml
  mcp:
    servers:
      fetch:
        command: "uvx"
        args: ["mcp-server-fetch"]
  ```
- **Programmatic Config**: Can define MCPSettings in code
  ```python
  from mcp_agent.config import MCPSettings, MCPServerSettings

  mcp_config = MCPSettings(
      servers={
          "todo_server": MCPServerSettings(
              command="...",
              args=[...]
          )
      }
  )
  context = RunnerContext(mcp_config=mcp_config)
  ```
- **Execution**: Pass context to Runner
  ```python
  result = await Runner.run(agent, input="...", context=context)
  ```

---

### 3. FastAPI - Server-Sent Events (SSE) Streaming
**Question**: How to implement async SSE streaming endpoints in FastAPI?

**Research Method**: Fetched FastAPI documentation via context-7 MCP (/fastapi/fastapi)

**Status**: RESOLVED

**Findings**:
- **StreamingResponse**: Use async generator pattern
  ```python
  from fastapi import FastAPI
  from fastapi.responses import StreamingResponse
  import asyncio

  app = FastAPI()

  async def generate_stream():
      for i in range(10):
          yield f"data: Item {i}\n\n"
          await asyncio.sleep(0.5)

  @app.get("/stream")
  async def stream_data():
      return StreamingResponse(generate_stream(), media_type="text/event-stream")
  ```
- **Media Type**: Use `"text/event-stream"` for SSE
- **Async Support**: FastAPI natively supports async generators
- **File Streaming**: Can use `yield from` for file-like objects

---

### 4. ChatKit Streaming Protocol
**Question**: How to implement ChatKit-compatible streaming with "Thinking" blocks and "Tool Calls"?

**Research Method**: Cross-referenced OpenAI Agents SDK streaming patterns with ChatKit requirements

**Status**: NEEDS CLARIFICATION

**Findings**:
- **OpenAI Agents SDK Streaming**: Use `Runner.run_streamed()` and iterate over events
  ```python
  result = Runner.run_streamed(agent, input="...", context=context)

  async for event in result.stream_events():
      if event.type == "raw_response_event":
          # Handle event
          pass
  ```
- **Event Types**: ResponseTextDeltaEvent, AgentUpdatedStreamEvent, etc.
- **NEEDS CLARIFICATION**: Exact mapping between Agents SDK events and ChatKit protocol
  - How to format "Thinking" blocks from agent reasoning
  - How to format "Tool Calls" from agent tool executions
  - Expected SSE event structure for ChatKit frontend

---

### 5. Pydantic Validation
**Question**: Best practices for validating natural language input in Pydantic models?

**Research Method**: General knowledge + FastAPI integration patterns

**Status**: RESOLVED

**Findings**:
- **Minimal Validation for NL Input**: Natural language input typically requires minimal validation (string type, max length)
- **Pydantic Models for API**:
  ```python
  from pydantic import BaseModel, Field

  class ChatRequest(BaseModel):
      input: str = Field(..., min_length=1, max_length=5000)
      conversation_id: str | None = None
  ```
- **Response Models**: Define structured response schemas
- **FastAPI Integration**: Automatic validation and OpenAPI schema generation

---

## Decisions Log

### Decision 1: Use agents_mcp Extension Instead of Raw MCP SDK
**Context**: Need to integrate MCP server tools with OpenAI Agents SDK for todo CRUD operations

**Options Considered**:
1. Raw MCP Python SDK with manual tool bridging
2. agents_mcp extension package (openai-agents-mcp)

**Decision**: Use agents_mcp extension package

**Rationale**:
- Provides native integration between OpenAI Agents SDK and MCP servers
- Handles tool discovery and registration automatically
- Supports both config file and programmatic configuration
- Maintains full Agents SDK functionality while adding MCP support

**Trade-offs**:
- Additional dependency (agents_mcp)
- Slightly less control over MCP client lifecycle
- Config file format specific to agents_mcp

**References**: /lastmile-ai/openai-agents-mcp (MCP Context7)

---

### Decision 2: Custom AsyncOpenAI Client for Gemini Bridge
**Context**: Constitution mandates Google Gemini 2.5 Flash as model provider, not OpenAI models

**Options Considered**:
1. Use OpenAI models (violates constitution)
2. Configure AsyncOpenAI with custom base_url pointing to Gemini endpoint
3. Build custom model provider from scratch

**Decision**: Configure AsyncOpenAI with custom base_url for Gemini

**Rationale**:
- Maintains compatibility with OpenAI Agents SDK (expects AsyncOpenAI client)
- Constitution requires Gemini bridge via AsyncOpenAI
- Uses `set_default_openai_client()` for SDK-wide configuration

**Trade-offs**:
- Requires Gemini endpoint to support OpenAI-compatible API format
- Potential compatibility issues with Gemini-specific features

**References**: /websites/openai_github_io_openai-agents-python (MCP Context7), Constitution.md

---

### Decision 3: FastAPI StreamingResponse for SSE
**Context**: Need to stream agent reasoning and tool execution to ChatKit frontend in real-time

**Options Considered**:
1. Standard JSON responses (no streaming)
2. WebSockets
3. Server-Sent Events (SSE) via FastAPI StreamingResponse

**Decision**: Use FastAPI StreamingResponse with SSE

**Rationale**:
- ChatKit protocol expects SSE-compatible streaming
- Simpler than WebSockets (unidirectional, no connection management)
- Native FastAPI support with async generators
- Standard `text/event-stream` media type

**Trade-offs**:
- Unidirectional only (client can't interrupt stream mid-execution)
- Requires careful event formatting for ChatKit compatibility

**References**: /fastapi/fastapi (MCP Context7)

---

### Decision 5: Tenacity for Retry Logic with Custom Circuit Breaker
**Context**: Need exponential backoff retry and circuit breaker pattern for external dependencies per clarifications (FR-012)

**Options Considered**:
1. pybreaker (synchronous only)
2. circuitbreaker (limited async)
3. tenacity with custom circuit breaker wrapper

**Decision**: Use tenacity for retry logic + custom circuit breaker state machine

**Rationale**:
- Tenacity provides native async/await support
- Built-in exponential backoff strategies
- Flexible stop conditions (max attempts, time limits)
- Simple circuit breaker wrapper can track failure counts and implement open/half-open states
- Well-maintained and widely used in async Python applications

**Trade-offs**:
- Custom circuit breaker requires ~50 lines of code vs off-the-shelf library
- Gained: Full control over circuit breaker logic, async compatibility, unified retry+circuit breaker pattern

**References**: tenacity documentation, async FastAPI patterns

---

### Decision 6: Python-JSON-Logger for Structured Logging
**Context**: Need structured JSON logging with request IDs per clarifications (FR-011)

**Options Considered**:
1. structlog (complex, flexible)
2. python-json-logger (simple, drop-in)

**Decision**: Use python-json-logger (pythonjsonlogger)

**Rationale**:
- Drop-in replacement for stdlib logging module
- Minimal configuration overhead
- JSON output format ready for log aggregation platforms
- Easy to inject request IDs via logging context
- Low performance overhead compared to structlog's processor pipeline

**Trade-offs**:
- Less flexible than structlog for complex log processing
- Gained: Simplicity, faster implementation, easier maintenance

**References**: FastAPI logging best practices

---

### Decision 7: Python 3.11-Slim-Bookworm Docker Base Image
**Context**: Need Docker containerization per clarifications (Assumption 7)

**Options Considered**:
1. python:3.11-alpine (smallest)
2. python:3.11-slim (balanced)
3. python:3.11-slim-bookworm (latest Debian)

**Decision**: Use python:3.11-slim-bookworm with multi-stage build

**Rationale**:
- Balance of size (~150MB after multi-stage build) vs package compatibility
- Debian Bookworm has better security update track record than Alpine
- Multi-stage build separates build dependencies from runtime image
- Easier to install system packages if needed (vs Alpine's musl libc issues)

**Trade-offs**:
- Slightly larger than Alpine (~50MB difference)
- Gained: Compatibility, security updates, easier maintenance

**References**: Docker Python official images, FastAPI containerization guides

---

### Decision 4: ChatKit Protocol Implementation - DEFERRED
**Context**: Need to format OpenAI Agents SDK stream events into ChatKit-compatible format

**Status**: DEFERRED - Requires ChatKit protocol specification

**Findings**:
- Agents SDK provides event stream via `Runner.run_streamed()`
- Events include: ResponseTextDeltaEvent, AgentUpdatedStreamEvent, tool execution events
- ChatKit expects "Thinking" blocks and "Tool Calls" in specific format

**Next Steps**:
- Document ChatKit protocol specification (if available)
- Create event mapper: Agents SDK events → ChatKit SSE format
- Implement in `src/streaming/chatkit.py`

---

## Technology Stack Summary (Post-Research)

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Web Framework | FastAPI | Latest (0.115+) | Async support, StreamingResponse, OpenAPI integration |
| AI Orchestration | openai-agents-python | Latest | Official OpenAI Agents SDK for agentic workflows |
| MCP Integration | agents_mcp | Latest | Native MCP server integration for Agents SDK |
| Model Provider | Google Gemini | 2.5-flash | Constitution mandate: cost efficiency, low latency |
| Model Client | AsyncOpenAI | Latest | Agents SDK compatibility with custom base_url |
| Streaming Protocol | FastAPI StreamingResponse | Native | SSE support for ChatKit frontend |
| Validation | Pydantic | 2.0+ | FastAPI native integration, data validation |
| Testing | pytest + pytest-asyncio + httpx | Latest | Async test support, HTTP client testing |
| Package Manager | uv | Latest | Constitution mandate: fast, deterministic |
| **Resilience** | tenacity | Latest | **NEW**: Exponential backoff + custom circuit breaker |
| **Logging** | python-json-logger | Latest | **NEW**: Structured JSON logging |
| **Containerization** | Docker (python:3.11-slim-bookworm) | 3.11+ | **NEW**: Deployment containerization |

---

### 6. Circuit Breaker Libraries
**Question**: Which circuit breaker library best integrates with FastAPI async patterns?

**Research Method**: Compare pybreaker, circuitbreaker, and tenacity for async support

**Status**: RESOLVED

**Findings**:
- **pybreaker**: Synchronous only, not suitable for async FastAPI
- **circuitbreaker**: Limited async support, basic functionality
- **tenacity**: Full async support with `@retry` decorator, exponential backoff built-in

**Decision**: Use **tenacity** for retry logic + custom circuit breaker wrapper
**Rationale**:
- Native async/await support (`async_retry`)
- Exponential backoff strategies built-in
- Flexible stop conditions (max attempts, time limits)
- Can wrap with simple circuit breaker state machine

---

### 7. Structured Logging Framework
**Question**: Which logging framework provides best JSON structured logging for FastAPI?

**Research Method**: Compare structlog vs python-json-logger

**Status**: RESOLVED

**Findings**:
- **structlog**:
  - Processor pipeline for structured data
  - Context binding for request IDs
  - More complex setup but more flexible

- **python-json-logger**:
  - Drop-in replacement for stdlib logging
  - Simpler integration with FastAPI
  - JSON output with minimal configuration

**Decision**: Use **python-json-logger** (pythonjsonlogger)
**Rationale**:
- Simpler integration with FastAPI logging
- Works with existing logging infrastructure
- Minimal performance overhead
- Easy to add request ID via logging context

---

### 8. Docker Base Image for FastAPI
**Question**: Which Docker base image balances size, security, and Python 3.11+ support?

**Research Method**: Best practices for FastAPI containerization

**Status**: RESOLVED

**Findings**:
- **python:3.11-slim**: Smaller than full image, Debian-based
- **python:3.11-alpine**: Smallest, but compilation issues with some packages
- **python:3.11-slim-bookworm**: Latest Debian stable, good security updates

**Decision**: Use **python:3.11-slim-bookworm** with multi-stage build
**Rationale**:
- Balance of size (~150MB) vs compatibility
- Better package availability than Alpine
- Multi-stage build separates build deps from runtime
- Regular security updates from Debian

---

## Next Steps

1. ~~Fetch MCP documentation for all dependencies~~ ✅
2. ~~Fill Decisions Log with findings~~ ✅
3. ~~Resolve all NEEDS CLARIFICATION items in plan.md~~ ✅
4. ~~Update Constitution Check status to PASS~~ ✅
5. ~~Proceed to Phase 1 (Design & Contracts)~~ ✅
6. ~~Update research.md with clarification decisions~~ ✅
7. **Next**: Update Phase 1 artifacts (data-model.md, contracts/, quickstart.md)
8. **Final**: Ready for `/sp.tasks` command

---

## Research Summary (Post-Clarifications)

**Total Decisions**: 7 (4 from initial planning + 3 from clarifications)

**Technology Stack Finalized**:
- ✅ OpenAI Agents SDK with agents_mcp extension
- ✅ AsyncOpenAI bridged to Gemini 2.5 Flash
- ✅ FastAPI with StreamingResponse for SSE
- ✅ **NEW**: Tenacity for exponential backoff + custom circuit breaker
- ✅ **NEW**: Python-json-logger for structured logging
- ✅ **NEW**: Docker (python:3.11-slim-bookworm) for containerization

**All NEEDS CLARIFICATION Resolved**: Yes (except ChatKit protocol details - acceptable for planning)

**Constitution Compliance**: All gates PASS

**Ready for Implementation**: Yes - proceed to `/sp.tasks` after Phase 1 artifact updates
