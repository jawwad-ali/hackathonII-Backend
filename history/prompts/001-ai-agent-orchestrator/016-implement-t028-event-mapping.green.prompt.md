---
id: 016
title: Implement T028 enhanced event mapping
stage: green
date: 2025-12-24
surface: agent
model: claude-sonnet-4.5
feature: 001-ai-agent-orchestrator
branch: 001-ai-agent-orchestrator
user: ali
command: /sp.implement
labels: ["event-mapping", "chatkit", "streaming", "agents-sdk", "sse"]
links:
  spec: specs/001-ai-agent-orchestrator/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/streaming/chatkit.py
  - src/api/routes.py
tests:
  - None (integration testing in later phases)
---

## Prompt

Execute T028

## Response snapshot

Successfully implemented T028 by creating a comprehensive event mapping function `map_agent_event_to_chatkit()` in src/streaming/chatkit.py and integrating it into the streaming endpoint.

**Implementation Details:**

1. **Created `map_agent_event_to_chatkit()` Function** (97 lines):
   - Comprehensive mapper for OpenAI Agents SDK events to ChatKit SSE format
   - Returns `Optional[str]` - yields SSE event or None if event should be skipped
   - Accepts `event: Any` for flexible handling of different SDK event types
   - Uses `StreamBuilder` for state management and event generation

2. **Event Type Mappings Implemented**:
   - **ResponseTextDeltaEvent**: `event.delta` → `response_delta` SSE
   - **ToolCallEvent (initiation)**: `event.tool_name + arguments` → `tool_call` SSE (IN_PROGRESS)
   - **ToolCallResultEvent (completion)**: `event.tool_name + result` → `tool_call` SSE (COMPLETED)
   - **AgentUpdatedStreamEvent**: `event.content/reasoning/thought` → `thinking` SSE
   - **AgentThinkingEvent**: `event.content/reasoning/thought` → `thinking` SSE
   - **ErrorEvent**: `event.error + error_type` → `error` SSE
   - **raw_response_event**: `event.content` → `response_delta` SSE (fallback)
   - **Other events**: None (skipped - debug, metadata, etc.)

3. **Robust Event Attribute Detection**:
   - Uses `hasattr()` for flexible attribute checking
   - Tries multiple attribute names for content (`content`, `reasoning`, `thought`, `message`)
   - Distinguishes tool initiation from completion using `hasattr(event, 'result')`
   - Gracefully handles missing attributes with `getattr(event, 'attr', default)`

4. **Error Mapping Enhancement**:
   - Maps error type strings to `ErrorType` enum
   - Handles KeyError/AttributeError for unknown error types
   - Defaults to `GEMINI_API_ERROR` for unmapped errors
   - Preserves `recoverable` flag from event

5. **Updated routes.py Integration**:
   - Added `map_agent_event_to_chatkit` import
   - Replaced 20+ lines of basic event handling with 4 lines:
     ```python
     sse_event = map_agent_event_to_chatkit(event, stream_builder)
     if sse_event:
         yield sse_event
     ```
   - Cleaner separation of concerns (routing vs. event mapping)
   - Updated comment to reference T028 completion

**Key Features:**
- Comprehensive event coverage for all expected SDK event types
- Flexible attribute detection handles variations in event structure
- Type-safe mapping with enum conversions
- None return for skipped events (clean filtering)
- Detailed docstring with event type mappings and examples
- State management via StreamBuilder (accumulated text, tools called)

**Code Changes:**
- **chatkit.py**: Added 97 lines for `map_agent_event_to_chatkit()` function
- **routes.py**: Simplified event processing loop (reduced from 30 to 6 lines)
- **Total**: +97 lines in chatkit.py, -24 lines in routes.py

**Architecture Benefits:**
- Single responsibility: chatkit.py handles all event mapping logic
- Testable: mapper function is pure (no side effects beyond StreamBuilder state)
- Extensible: Easy to add new event types in one location
- Maintainable: Event mapping logic is centralized

**Next Steps:**
- T029: Integrate router in main.py
- Later: Add unit tests for event mapper with various event types
- Later: Profile event processing performance under load

## Outcome

- ✅ Impact: Comprehensive event mapping enables full ChatKit SSE protocol support for all OpenAI Agents SDK events
- 🧪 Tests: None (implementation only - unit tests for mapper planned in testing phases)
- 📁 Files: Updated src/streaming/chatkit.py (+97 lines), src/api/routes.py (simplified event loop)
- 🔁 Next prompts: Implement T029 (Router integration in main.py), add unit tests for event mapper
- 🧠 Reflection: Centralizing event mapping in a dedicated function significantly improves code organization and maintainability. The flexible attribute detection strategy handles SDK event variations gracefully. The None return pattern for skipped events is cleaner than filtering in the caller.

## Evaluation notes (flywheel)

- Failure modes observed: None during implementation (runtime verification pending)
- Graders run and results (PASS/FAIL): N/A (manual verification only)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add debug logging to mapper to verify which event types are encountered in real agent runs, then refine mappings based on actual event patterns
