---
id: PHR-020
title: Implement Retry Exponential Backoff
stage: green
date: 2025-12-25T00:00:00Z
surface: claude-code-cli
model: claude-sonnet-4-5
feature: 001-ai-agent-orchestrator
branch: 001-ai-agent-orchestrator
user: Ali jawwad
command: /sp.implement
labels: [resilience, retry, tenacity, exponential-backoff, phase-5]
links:
  spec: specs/001-ai-agent-orchestrator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - path: src/resilience/retry.py
    status: created
    lines_added: 249
  - path: specs/001-ai-agent-orchestrator/tasks.md
    status: modified
    lines_modified: 1
tests:
  - type: validation
    description: Python syntax validation passed
    status: passed
---

## Prompt

Now lets execute task number T033 CAREFULLY

## Response snapshot

Successfully completed task T033 from Phase 5: Resilience Implementation.

**T033: Create src/resilience/retry.py with tenacity exponential backoff configuration**

Implemented comprehensive retry logic module with tenacity-based exponential backoff configurations in `src/resilience/retry.py:1-249` (249 lines).

**Key Components Implemented:**

1. **Retriable Exceptions Configuration** (lines 22-27):
   - `ConnectionError` - Service unreachable
   - `TimeoutError` - Service slow/unresponsive
   - `OSError` - Network-related OS errors
   - Excludes rate limit errors (429) - handled separately by circuit breaker

2. **MCP Server Retry Decorator** (lines 30-70):
   - `create_mcp_retry_decorator()` - Factory function
   - **Max attempts**: 5 (1 initial + 4 retries)
   - **Exponential backoff**: 1s → 2s → 4s → 8s → 16s (with jitter)
   - **Max wait**: 30 seconds
   - **Jitter**: Automatic via tenacity (prevents thundering herd)
   - **Logging**: Warning before sleep, Info after attempt
   - **Behavior**: Re-raises exception after all retries exhausted

3. **Gemini API Retry Decorator** (lines 73-121):
   - `create_gemini_retry_decorator()` - Factory function
   - **Max attempts**: 3 (stricter due to external API rate limits)
   - **Exponential backoff**: 2s → 4s → 8s (with jitter)
   - **Max wait**: 60 seconds (longer for external API)
   - **Multiplier**: 2 (longer initial wait)
   - **Logging**: Warning before sleep, Info after attempt
   - **Behavior**: Re-raises exception after all retries exhausted

4. **Custom Retry Decorator** (lines 124-171):
   - `create_custom_retry_decorator()` - Configurable factory
   - **Parameters**: max_attempts, min_wait, max_wait, multiplier, retriable_exceptions
   - **Use case**: Fine-tuning for specific external services beyond MCP/Gemini

5. **Convenience Decorators** (lines 174-175):
   - `mcp_retry` - Pre-configured MCP retry decorator
   - `gemini_retry` - Pre-configured Gemini retry decorator
   - **Direct usage**: `@mcp_retry` or `@gemini_retry`

**Usage Examples Documented** (lines 178-249):

1. **Simple MCP Call**:
   ```python
   @mcp_retry
   async def fetch_todos_from_mcp():
       return await mcp_client.call_tool("list_todos", {})
   ```

2. **Simple Gemini Call**:
   ```python
   @gemini_retry
   async def generate_response(prompt: str):
       return await gemini_client.chat.completions.create(...)
   ```

3. **Combined with Circuit Breaker** (recommended pattern):
   ```python
   @mcp_retry
   async def call_with_retry(tool_name, args):
       return await mcp_client.call_tool(tool_name, args)

   async def call_mcp_with_resilience(tool_name, args):
       return await breaker.call(call_with_retry, tool_name, args)
   ```
   - **Execution flow**: Circuit breaker → Retry logic → Actual call
   - **Benefit**: Fail-fast when circuit open, retry with backoff when closed

4. **Custom Configuration**:
   ```python
   custom_retry = create_custom_retry_decorator(
       max_attempts=7, min_wait=3, max_wait=120, multiplier=2
   )
   ```

**Configuration Details:**

**MCP Server** (more tolerant):
- Threshold: 5 attempts (local service, expect higher availability)
- Initial wait: 1 second
- Max wait: 30 seconds
- Rationale: Local MCP server should recover quickly, but allow more retries

**Gemini API** (stricter):
- Threshold: 3 attempts (external API, rate limits apply)
- Initial wait: 2 seconds (longer to avoid rate limits)
- Max wait: 60 seconds (external API may have longer recovery)
- Rationale: External API has rate limits, fewer retries to avoid quota exhaustion

**Tenacity Features Used:**
- `stop_after_attempt()` - Max retry limit
- `wait_exponential()` - Exponential backoff with jitter
- `retry_if_exception_type()` - Selective retry on specific exceptions
- `before_sleep_log()` - Log before waiting
- `after_log()` - Log after attempt
- `reraise=True` - Re-raise exception after exhaustion

**Integration Readiness:**

Prepares for T034-T035:
- T034: Wrap MCP client calls → Use `@mcp_retry` decorator
- T035: Wrap Gemini calls → Use `@gemini_retry` decorator
- Circuit breaker will wrap retry logic for complete resilience

**Alignment:**

- Implements FR-012 (exponential backoff for external dependencies)
- Follows research.md Decision 5 (tenacity for retry logic)
- Async-compatible for FastAPI/MCP integration
- Logging ready for Phase 6 structured logging integration

**Validation:**

- Python syntax validation: PASS
- File created successfully: 249 lines
- Decorators properly configured with tenacity

## Outcome

- ✅ Impact: Complete retry logic with exponential backoff for MCP and Gemini. Ready for integration in T034-T035.
- 🧪 Tests: Syntax validation passed. Runtime tests will be performed during integration (T034-T035) and Phase 11.
- 📁 Files: Created retry.py (249 lines), updated tasks.md
- 🔁 Next prompts: Execute T034 (wrap MCP client with circuit breaker + retry), T035 (wrap Gemini with circuit breaker + retry)
- 🧠 Reflection: Clean separation of MCP vs Gemini configurations reflects different SLAs and reliability expectations. Documented usage examples ensure proper integration pattern (circuit breaker wraps retry logic). Tenacity's native async support ensures compatibility with FastAPI streaming.

## Evaluation notes (flywheel)

- Failure modes observed: None. Syntax validation passed.
- Graders run and results (PASS/FAIL): Syntax check PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Integrate retry decorators into MCP client (T034) and observe backoff behavior under simulated connection failures
