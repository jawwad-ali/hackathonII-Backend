---
name: test-gen
description: Generate comprehensive pytest integration tests for MCP tools and FastAPI endpoints. Includes fixtures, edge cases, and validation tests.
---

# Pytest Test Generator

## Purpose
Auto-generate integration tests following project's pytest patterns with proper fixtures, database sessions, and >80% coverage for business logic.

## Core Rules
1. **Context7 First**: Query `/websites/sqlmodel_tiangolo` for testing patterns
2. **Use Project Fixtures**: Leverage `conftest.py` fixtures (session, sample_todo, sample_todos)
3. **Test-Driven**: Generate tests BEFORE or ALONGSIDE implementation
4. **Coverage Target**: >80% for business logic
5. **Integration Focus**: Test database persistence, not mocks

## Workflow
1. **Identify Target**: MCP tool or FastAPI endpoint to test
2. **Read conftest.py**: Understand available fixtures
3. **Query Context7**: Fetch SQLModel + FastAPI testing patterns
4. **Generate Test Suite**:

### For MCP Tools
```python
import pytest
from sqlmodel import select
from src.mcp_server.models import Todo, TodoStatus
from src.mcp_server.tools.operation_name import operation_name

def test_operation_success(session):
    """Test successful operation with valid input."""
    result = operation_name(
        param="value",
        _test_session=session
    )

    import json
    data = json.loads(result)

    assert data["success"] is True
    assert "data" in data

    # Verify database persistence
    statement = select(Todo).where(Todo.id == data["data"]["id"])
    todo = session.exec(statement).first()

    assert todo is not None
    assert todo.title == "Expected Value"


def test_operation_not_found(session):
    """Test operation with non-existent resource."""
    result = operation_name(
        param="nonexistent",
        _test_session=session
    )

    import json
    data = json.loads(result)

    assert data["success"] is False
    assert "error" in data


def test_operation_validation_error(session):
    """Test operation with invalid input."""
    result = operation_name(
        param="",  # Invalid empty string
        _test_session=session
    )

    import json
    data = json.loads(result)

    assert data["success"] is False


def test_operation_with_optional_params(session):
    """Test operation with all optional parameters."""
    result = operation_name(
        required_param="value",
        optional_param="extra",
        _test_session=session
    )

    import json
    data = json.loads(result)

    assert data["success"] is True
```

### For FastAPI Endpoints
```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_create_endpoint(session):
    """Test POST endpoint with valid data."""
    response = client.post(
        "/todos/",
        json={"title": "Test Todo", "description": "Test"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Test Todo"
    assert data["id"] is not None

    # Verify database
    from src.mcp_server.models import Todo
    from sqlmodel import select
    todo = session.exec(select(Todo).where(Todo.id == data["id"])).first()
    assert todo is not None


def test_create_endpoint_validation_error(session):
    """Test POST endpoint with missing required field."""
    response = client.post("/todos/", json={"description": "No title"})

    assert response.status_code == 422  # Validation error


def test_get_endpoint_not_found(session):
    """Test GET endpoint with non-existent ID."""
    response = client.get("/todos/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

## Test Categories

### Happy Path Tests
- Valid input with all required fields
- Valid input with optional fields
- Successful database persistence

### Edge Cases
- Empty strings
- Maximum length values
- Boundary values (offset=0, limit=100)
- Special characters

### Error Cases
- Missing required fields (422)
- Resource not found (404)
- Invalid enum values
- Duplicate constraints

### Integration Tests
- Verify database state after operations
- Test cascading operations
- Check related entity updates

## Output Format
- Complete test file with imports
- Descriptive test names and docstrings
- Multiple test functions covering scenarios
- Proper assertions (success, data, database state)
- Uses project fixtures (session, sample_todo)

## Quality Checks
- ✓ Each test has clear docstring
- ✓ Uses _test_session for MCP tools
- ✓ Verifies database persistence
- ✓ Tests both success and failure paths
- ✓ Assertions check JSON structure
- ✓ Follows naming: test_<operation>_<scenario>

## Example Usage
User: "Generate tests for update_todo tool"
Action: Read update_todo.py → Query Context7 → Generate test_update_todo.py with 5-7 test cases → Verify fixture usage
