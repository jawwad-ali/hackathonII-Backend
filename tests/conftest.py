"""Root pytest configuration and shared fixtures.

This module provides test fixtures shared across all test modules:
- FastAPI TestClient for API testing
- Database fixtures (re-exported from mcp_server)
- Mock fixtures for external services
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session, SQLModel, create_engine

from src.main import app
from src.mcp_server.models import Todo, TodoStatus, TodoPriority


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================

@pytest.fixture(name="client")
def client_fixture():
    """FastAPI test client for API endpoint testing.

    Provides a synchronous test client for testing HTTP endpoints.
    Use this for testing /health, /chat/stream, and other routes.

    Yields:
        TestClient: FastAPI test client instance
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(name="client_no_lifespan")
def client_no_lifespan_fixture():
    """FastAPI test client without lifespan events.

    Useful for testing endpoints in isolation without MCP server startup.
    """
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# =============================================================================
# Database Fixtures (shared across all tests)
# =============================================================================

@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Creates a test database engine using SQLite in-memory.

    This fixture creates a fresh SQLite in-memory database for each test,
    ensuring test isolation and fast execution.

    Yields:
        Engine: SQLModel engine connected to in-memory SQLite database
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(test_engine):
    """Provides a test database session with automatic cleanup.

    Args:
        test_engine: The test database engine fixture

    Yields:
        Session: SQLModel session for database operations
    """
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="sample_todo")
def sample_todo_fixture(session):
    """Creates a single sample todo for testing.

    Returns:
        Todo: A sample active todo persisted in test database
    """
    todo = Todo(
        title="Sample Todo",
        description="This is a sample todo for testing",
        status=TodoStatus.ACTIVE,
        priority=TodoPriority.MEDIUM
    )
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


@pytest.fixture(name="sample_todos")
def sample_todos_fixture(session):
    """Creates multiple sample todos with different statuses.

    Returns:
        list[Todo]: List of todos with ACTIVE, COMPLETED, ARCHIVED statuses
    """
    todos = [
        Todo(title="Active Todo 1", description="First active", status=TodoStatus.ACTIVE),
        Todo(title="Active Todo 2", description="Second active", status=TodoStatus.ACTIVE),
        Todo(title="Completed Todo", description="Done task", status=TodoStatus.COMPLETED),
        Todo(title="Archived Todo", description="Old task", status=TodoStatus.ARCHIVED),
    ]
    for todo in todos:
        session.add(todo)
    session.commit()
    for todo in todos:
        session.refresh(todo)
    return todos


@pytest.fixture(name="sample_todos_with_priority")
def sample_todos_with_priority_fixture(session):
    """Creates todos with varied priorities and statuses for filter testing.

    Returns:
        list[Todo]: Comprehensive list for testing priority/status combinations
    """
    todos = [
        Todo(title="High active", status=TodoStatus.ACTIVE, priority=TodoPriority.HIGH),
        Todo(title="Medium active", status=TodoStatus.ACTIVE, priority=TodoPriority.MEDIUM),
        Todo(title="Low active", status=TodoStatus.ACTIVE, priority=TodoPriority.LOW),
        Todo(title="High completed", status=TodoStatus.COMPLETED, priority=TodoPriority.HIGH),
        Todo(title="Medium completed", status=TodoStatus.COMPLETED, priority=TodoPriority.MEDIUM),
        Todo(title="High archived", status=TodoStatus.ARCHIVED, priority=TodoPriority.HIGH),
    ]
    for todo in todos:
        session.add(todo)
    session.commit()
    for todo in todos:
        session.refresh(todo)
    return todos


@pytest.fixture(name="many_todos")
def many_todos_fixture(session):
    """Creates 10 todos for testing batch operations and confirmation flows.

    Returns:
        list[Todo]: 10 active todos for mass deletion testing
    """
    todos = [
        Todo(
            title=f"Task {i}",
            description=f"Description for task {i}",
            status=TodoStatus.ACTIVE,
            priority=TodoPriority.MEDIUM
        )
        for i in range(1, 11)
    ]
    for todo in todos:
        session.add(todo)
    session.commit()
    for todo in todos:
        session.refresh(todo)
    return todos


# =============================================================================
# Mock Fixtures for External Services
# =============================================================================

@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing without actual MCP connection."""
    with patch("src.orchestrators.todo_agent.MCPServerStdio") as mock:
        mock_instance = MagicMock()
        mock_instance.call_tool = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing without actual API calls."""
    with patch("src.orchestrators.todo_agent.AsyncOpenAI") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


# =============================================================================
# Circuit Breaker Fixtures
# =============================================================================

@pytest.fixture
def reset_circuit_breakers():
    """Reset all circuit breakers to CLOSED state before test."""
    from src.mcp.client import get_mcp_circuit_breaker
    from src.config import get_llm_circuit_breaker
    from src.resilience.circuit_breaker import CircuitState

    mcp_breaker = get_mcp_circuit_breaker()
    llm_breaker = get_llm_circuit_breaker()

    # Reset to closed state
    mcp_breaker.state.state = CircuitState.CLOSED
    mcp_breaker.state.failure_count = 0
    llm_breaker.state.state = CircuitState.CLOSED
    llm_breaker.state.failure_count = 0

    yield

    # Cleanup after test
    mcp_breaker.state.state = CircuitState.CLOSED
    mcp_breaker.state.failure_count = 0
    llm_breaker.state.state = CircuitState.CLOSED
    llm_breaker.state.failure_count = 0
