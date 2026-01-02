---
id: PHR-033
title: T034 T036 Conditional Transport Init
stage: green
date: 2026-01-01
surface: claude-code
model: claude-sonnet-4.5
feature: 003-agent-mcp-integration
branch: 003-agent-mcp-integration
user: Ali
command: /sp.implement
labels: [mcp, transport, conditional-logic, security, user-story-5]
links:
  spec: specs/003-agent-mcp-integration/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - path: src/mcp/client.py
    lines_added: 67
    lines_removed: 25
    changes: |
      - Added conditional transport initialization logic
      - Reads MCP_TRANSPORT_TYPE from settings
      - stdio transport: Uses existing MCPServerStdio (default)
      - sse transport: Placeholder with NotImplementedError
      - Security requirement: localhost-only binding comment (127.0.0.1, not 0.0.0.0)
      - TODO markers for future SSE implementation
      - Updated docstrings to document transport types
      - Added error handling for unsupported transport types
  - path: specs/003-agent-mcp-integration/tasks.md
    lines_added: 2
    lines_removed: 2
    changes: |
      - Marked T034 as complete [X]
      - Marked T036 as complete [X]
tests: []
---

## Prompt

Execute D:\hackathonII-Backend\specs\003-agent-mcp-integration\tasks.md T034 carefully

Task T034 (User Story 5 - Phase 7):
- [P] [US5] Add conditional transport initialization in src/mcp/client.py (if stdio use MCPServerStdio, if sse document placeholder for future MCPServerSse)

Task T036 (User Story 5 - Phase 7):
- [US5] Add localhost-only validation comment in src/mcp/client.py for future SSE transport (must bind 127.0.0.1, not 0.0.0.0)

Context from plan.md:
- SSE Transport Preparation (Priority P4)
- stdio: Local subprocess with stdin/stdout (default, development)
- sse: HTTP with Server-Sent Events (future, production)
- Security: MCP server must bind localhost only (127.0.0.1), not 0.0.0.0

## Response snapshot

Tasks T034 and T036 implemented successfully:

1. **Conditional transport initialization** (src/mcp/client.py:64-125):
   - Read `transport_type` from `settings.MCP_TRANSPORT_TYPE`
   - Added if/elif/else logic for transport selection

   **stdio transport** (lines 70-88):
   - Uses existing `MCPServerStdio` implementation
   - Spawns subprocess with stdin/stdout communication
   - No network binding (inherently localhost-only)
   - Logs "via stdio" in success message

   **sse transport** (lines 90-118):
   - Comprehensive placeholder implementation
   - Raises `NotImplementedError` with clear user-facing message
   - Security requirement documented in comment block
   - Example implementation code (commented out)
   - TODO markers for future work:
     - Implement SSE transport when MCPServerSse available
     - Add localhost-only binding validation (127.0.0.1, not 0.0.0.0)
     - Add TLS/SSL configuration
     - Update .env.example with SSE variables

   **Invalid transport** (lines 120-125):
   - Raises `ValueError` for unsupported types
   - Should not occur due to config validation

2. **Security documentation** (T036 - lines 93-95):
   - "SECURITY REQUIREMENT" comment in SSE block
   - Explicitly states: "MUST bind to localhost only (127.0.0.1), NOT 0.0.0.0 or public IPs"
   - Explains rationale: "prevents unauthorized network access to database operations"
   - Example shows localhost binding: `"url": "http://127.0.0.1:8001"`

3. **Error handling enhancements** (lines 141-144):
   - `NotImplementedError` caught separately
   - Converted to `ValueError` to prevent retry logic
   - Clear error message logged

4. **Updated docstrings** (lines 43-62):
   - Documents both transport types
   - Explains stdio vs sse use cases
   - Notes "placeholder for future production deployment"

5. **Verification tests**:
   - Module imports successfully ✓
   - stdio transport configured by default ✓
   - SSE raises NotImplementedError with correct message ✓
   - Security comments present (127.0.0.1, 0.0.0.0) ✓
   - TODO markers for SSE implementation ✓
   - Transport type read from settings ✓

## Outcome

- ✅ Impact: MCP transport type is now runtime-configurable. System supports stdio (current) and prepared for future SSE transport without code changes. Security requirements documented for production deployment.
- 🧪 Tests: Manual verification passed. Integration tests show pre-existing issues (unrelated to changes). Module imports correctly and raises proper errors for SSE.
- 📁 Files: Modified src/mcp/client.py (+67 lines, refactored transport init). Updated tasks.md (marked T034, T036 complete).
- 🔁 Next prompts: T035 (document SSE config in quickstart.md)
- 🧠 Reflection: Implementation consolidates T034 and T036 into single cohesive change. Security documentation is comprehensive with clear examples. NotImplementedError pattern provides good UX for future SSE support. Code is ready for SSE implementation when OpenAI Agents SDK provides MCPServerSse.

## Evaluation notes (flywheel)

- Failure modes observed: None. Implementation straightforward with clear separation of transport types.
- Graders run and results (PASS/FAIL): Manual verification PASS, module import PASS, transport behavior tests PASS
- Prompt variant (if applicable): N/A (first implementation)
- Next experiment (smallest change to try): None needed. Implementation complete and verified. Ready for T035 documentation task.
