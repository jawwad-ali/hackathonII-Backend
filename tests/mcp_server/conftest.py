"""Pytest configuration and fixtures for MCP server tests.

This module provides test fixtures for database sessions, test data,
and other test utilities. Uses SQLite in-memory database for fast,
isolated testing.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.mcp_server.models import Todo, TodoStatus


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Creates a test database engine using SQLite in-memory.

    This fixture creates a fresh SQLite in-memory database for each test,
    ensuring test isolation and fast execution.

    Yields:
        Engine: SQLModel engine connected to in-memory SQLite database
    """
    # Create in-memory SQLite engine for testing
    # connect_args needed for SQLite to work with SQLModel
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL query debugging
    )

    # Create all tables in the test database
    SQLModel.metadata.create_all(engine)

    yield engine

    # Cleanup: Drop all tables after test
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(test_engine):
    """Provides a test database session with automatic rollback.

    This fixture creates a new session for each test and automatically
    rolls back changes after the test completes, ensuring test isolation.

    Args:
        test_engine: The test database engine fixture

    Yields:
        Session: SQLModel session for database operations
    """
    with Session(test_engine) as session:
        yield session
        # Session will automatically close when exiting context


@pytest.fixture(name="sample_todo")
def sample_todo_fixture(session):
    """Creates a sample todo for testing.

    Provides a pre-created todo with known values for use in tests
    that need existing data.

    Args:
        session: The test database session fixture

    Returns:
        Todo: A sample todo object persisted in the test database
    """
    todo = Todo(
        title="Sample Todo",
        description="This is a sample todo for testing",
        status=TodoStatus.ACTIVE
    )
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


@pytest.fixture(name="sample_todos")
def sample_todos_fixture(session):
    """Creates multiple sample todos with different statuses.

    Provides a collection of todos for testing list/search operations.

    Args:
        session: The test database session fixture

    Returns:
        list[Todo]: List of sample todo objects with varied data
    """
    todos = [
        Todo(
            title="Active Todo 1",
            description="First active todo",
            status=TodoStatus.ACTIVE
        ),
        Todo(
            title="Active Todo 2",
            description="Second active todo",
            status=TodoStatus.ACTIVE
        ),
        Todo(
            title="Completed Todo",
            description="This one is done",
            status=TodoStatus.COMPLETED
        ),
        Todo(
            title="Archived Todo",
            description="Old todo for reference",
            status=TodoStatus.ARCHIVED
        ),
    ]

    for todo in todos:
        session.add(todo)

    session.commit()

    # Refresh all todos to get their IDs
    for todo in todos:
        session.refresh(todo)

    return todos
