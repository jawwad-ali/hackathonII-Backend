# Phase 1 Development Skills

Production-ready skills for accelerating Feature 002 (MCP Server CRUD Operations).

## Available Skills

### 1. `/crud-gen` - FastAPI CRUD Generator
**Purpose**: Auto-scaffold complete CRUD endpoints for SQLModel entities

**When to Use**:
- Starting new resource endpoints (todos, users, tasks, etc.)
- Need consistent pagination, validation, error handling
- Want FastAPI + SQLModel best practices

**Example Usage**:
```
/crud-gen for Todo model with all CRUD operations
```

**Generates**:
- Complete schemas (Base, Create, Update, Public)
- 5 endpoints (POST, GET list, GET by ID, PATCH, DELETE)
- Session dependency injection
- Proper error handling (404, 422)
- Pagination (offset, limit ≤100)

---

### 2. `/mcp-scaffold` - MCP Tool Scaffolder
**Purpose**: Generate FastMCP tool implementations with error handling and test support

**When to Use**:
- Implementing new MCP tools (update_todo, search_todos, delete_todo)
- Need consistent error handling and logging
- Want test-friendly tool structure

**Example Usage**:
```
/mcp-scaffold update_todo tool with status and description fields
```

**Generates**:
- Complete tool function with `@mcp.tool()` decorator
- Error handling with try-catch and logging
- Test session support (`_test_session` parameter)
- JSON response structure (success/error)
- Proper SQLModel queries

---

### 3. `/test-gen` - Pytest Test Generator
**Purpose**: Generate comprehensive integration tests for tools and endpoints

**When to Use**:
- After implementing MCP tool or endpoint
- Need >80% test coverage
- Want happy path + edge cases + error scenarios

**Example Usage**:
```
/test-gen for update_todo tool
```

**Generates**:
- Multiple test functions (5-7 per target)
- Happy path tests (valid input)
- Edge cases (empty strings, boundaries)
- Error tests (404, validation)
- Database persistence verification
- Uses project fixtures (session, sample_todo)

---

## Workflow Integration

### Recommended Development Cycle

#### Option 1: Test-Driven Development
```
1. /mcp-scaffold <tool-name>     → Generate tool structure
2. /test-gen for <tool-name>     → Generate tests FIRST
3. Run: uv run pytest -k <tool>  → See tests fail (red)
4. Implement tool logic           → Make tests pass (green)
5. Refactor if needed             → Keep tests green
```

#### Option 2: Endpoint-First Development
```
1. /crud-gen for <Model>         → Generate endpoints
2. /test-gen for <endpoint>      → Generate endpoint tests
3. /mcp-scaffold <related-tool>  → Add MCP tools if needed
4. /test-gen for <tool>          → Test MCP tools
5. Run: uv run pytest            → Verify all pass
```

---

## Quick Reference

### Completing Feature 002 (MCP CRUD Operations)

**User Story 2: Update Todo** (T021-T029)
```bash
# Step 1: Generate tool
/mcp-scaffold update_todo with title, description, and status

# Step 2: Generate tests
/test-gen for update_todo tool

# Step 3: Run tests
uv run pytest tests/mcp_server/test_update_todo.py -v

# Step 4: Fix any issues and verify
uv run pytest --cov=src/mcp_server/tools
```

**User Story 3: Search Todos** (T030-T038)
```bash
/mcp-scaffold search_todos with title, description, status filters
/test-gen for search_todos tool
uv run pytest tests/mcp_server/test_search_todos.py -v
```

**User Story 4: Delete Todo** (T039-T046)
```bash
/mcp-scaffold delete_todo with soft delete (status=ARCHIVED)
/test-gen for delete_todo tool
uv run pytest tests/mcp_server/test_delete_todo.py -v
```

---

## Skill Conventions

### All Skills Follow
1. **Context7 First**: Query documentation before generating code
2. **uv Only**: Never suggest pip commands
3. **Type Safety**: Python 3.10+ union types (`int | None`)
4. **Error Handling**: Try-catch with proper logging
5. **Test Support**: All generated code is testable

### Code Quality Standards
- ✓ Descriptive docstrings for LLM understanding
- ✓ Type hints on all parameters
- ✓ Proper session management (no leaks)
- ✓ JSON responses for MCP tools
- ✓ HTTPException for FastAPI errors
- ✓ Database persistence verification in tests

---

## Environment Setup

Before using any skill, ensure your environment is ready:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/macOS

# Install dependencies
uv pip install -e .

# Verify database connection
# Check DATABASE_URL in .env

# Run existing tests to verify setup
uv run pytest
```

---

## Troubleshooting

### Skill Not Found
```bash
# List available skills
ls .claude/skills/

# Verify skill name matches directory
/crud-gen  # ✓ Correct
/generate-crud  # ✗ Wrong
```

### Generated Code Has Errors
1. Check Context7 queries ran successfully
2. Verify .env has all required variables
3. Ensure uv dependencies are installed
4. Check SQLModel entity exists

### Tests Failing
1. Verify database is accessible
2. Check fixtures in conftest.py
3. Ensure tool is registered in server.py
4. Run with verbose: `uv run pytest -vv`

---

## Examples

### Full Feature Implementation
```bash
# Scenario: Implement User Management

# 1. Generate CRUD endpoints
/crud-gen for User model with email, name, role fields

# 2. Generate endpoint tests
/test-gen for User endpoints

# 3. Generate MCP tools
/mcp-scaffold create_user tool
/mcp-scaffold list_users tool
/mcp-scaffold update_user tool
/mcp-scaffold delete_user tool

# 4. Generate tool tests
/test-gen for create_user tool
/test-gen for list_users tool
/test-gen for update_user tool
/test-gen for delete_user tool

# 5. Verify everything
uv run pytest --cov=src --cov-report=term-missing
```

---

## Contributing New Skills

If you need a skill not covered by Phase 1:

1. Create `.claude/skills/<skill-name>/SKILL.md`
2. Follow the structure in existing skills
3. Include:
   - Frontmatter (name, description)
   - Purpose and Core Rules
   - Workflow steps
   - Output format
   - Quality checks
   - Example usage

---

## Next Phases

**Phase 2**: Agent Integration Skills (Feature 003)
- `/integrate-agent-mcp` - Connect agent to MCP server
- `/add-circuit-breaker` - Wrap calls with resilience

**Phase 3**: ChatKit Integration Skills (Feature 004)
- `/add-streaming` - Implement streaming endpoints
- `/add-health-check` - Comprehensive health monitoring

---

**Version**: 1.0.0
**Last Updated**: 2026-01-10
**Compatible With**: hackathonII-Backend Feature 002
