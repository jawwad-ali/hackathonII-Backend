"""Integration tests for MCP tools (create_todo and list_todos).

These tests verify that MCP tools interact correctly with the database,
validate inputs properly, and return MCP-compliant Content objects.

Note: Tools will be implemented as functions decorated with @mcp.tool.
These tests are written FIRST (TDD approach) and will initially FAIL.
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import select

from src.mcp_server.models import Todo, TodoStatus
from src.mcp_server.schemas import CreateTodoInput


class TestCreateTodoTool:
    """Integration tests for create_todo MCP tool.

    Tests cover:
    - Successful todo creation with valid inputs
    - Input validation (title length, description length)
    - Database persistence
    - MCP response format compliance
    - Error handling for invalid inputs
    """

    def test_create_todo_with_title_only(self, session):
        """Test creating a todo with only title (minimal valid input)."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "Call dentist"

        # Act
        result = create_todo(title=title, _test_session=session)

        # Assert - Verify todo was created in database
        statement = select(Todo).where(Todo.title == title)
        db_result = session.exec(statement)
        created_todo = db_result.first()

        assert created_todo is not None
        assert created_todo.title == title
        assert created_todo.description is None
        assert created_todo.status == TodoStatus.ACTIVE
        assert created_todo.id is not None

        # Assert - Verify MCP response format
        assert isinstance(result, str)  # FastMCP tools return strings
        assert "created successfully" in result.lower() or "todo created" in result.lower()
        assert title in result

    def test_create_todo_with_title_and_description(self, session):
        """Test creating a todo with both title and description."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "Buy groceries"
        description = "Milk, eggs, bread, and coffee beans"

        # Act
        result = create_todo(title=title, description=description, _test_session=session)

        # Assert - Verify todo was created in database
        statement = select(Todo).where(Todo.title == title)
        db_result = session.exec(statement)
        created_todo = db_result.first()

        assert created_todo is not None
        assert created_todo.title == title
        assert created_todo.description == description
        assert created_todo.status == TodoStatus.ACTIVE

        # Assert - Verify MCP response format
        assert isinstance(result, str)
        assert title in result

    def test_create_todo_with_long_title(self, session):
        """Test creating a todo with maximum valid title length (200 chars)."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "A" * 200  # Maximum allowed length

        # Act
        result = create_todo(title=title, _test_session=session)

        # Assert - Verify todo was created
        statement = select(Todo).where(Todo.title == title)
        db_result = session.exec(statement)
        created_todo = db_result.first()

        assert created_todo is not None
        assert len(created_todo.title) == 200

    def test_create_todo_with_long_description(self, session):
        """Test creating a todo with maximum valid description length (2000 chars)."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "Test todo"
        description = "A" * 2000  # Maximum allowed length

        # Act
        result = create_todo(title=title, description=description, _test_session=session)

        # Assert - Verify todo was created
        statement = select(Todo).where(Todo.title == title)
        db_result = session.exec(statement)
        created_todo = db_result.first()

        assert created_todo is not None
        assert len(created_todo.description) == 2000

    def test_create_todo_title_exceeds_max_length(self):
        """Test that title exceeding 200 chars raises validation error."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "A" * 201  # Exceeds maximum length

        # Act & Assert - Should raise validation error
        with pytest.raises(Exception) as exc_info:
            create_todo(title=title, _test_session=None)

        # Verify error mentions validation or length
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "length" in error_message or "max" in error_message

    def test_create_todo_description_exceeds_max_length(self):
        """Test that description exceeding 2000 chars raises validation error."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "Test"
        description = "A" * 2001  # Exceeds maximum length

        # Act & Assert - Should raise validation error
        with pytest.raises(Exception) as exc_info:
            create_todo(title=title, description=description, _test_session=None)

        # Verify error mentions validation or length
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "length" in error_message or "max" in error_message

    def test_create_todo_empty_title(self):
        """Test that empty title raises validation error."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = ""  # Empty string

        # Act & Assert - Should raise validation error
        with pytest.raises(Exception) as exc_info:
            create_todo(title=title, _test_session=None)

        # Verify error mentions validation or empty
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "empty" in error_message or "required" in error_message

    def test_create_todo_whitespace_only_title(self):
        """Test that whitespace-only title raises validation error."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "   \t\n   "  # Only whitespace

        # Act & Assert - Should raise validation error
        with pytest.raises(Exception) as exc_info:
            create_todo(title=title, _test_session=None)

        # Verify error mentions validation or whitespace/empty
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "empty" in error_message or "whitespace" in error_message

    def test_create_todo_strips_whitespace_from_title(self, session):
        """Test that leading/trailing whitespace is stripped from title."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title_with_whitespace = "  Buy groceries  "
        expected_title = "Buy groceries"

        # Act
        result = create_todo(title=title_with_whitespace, _test_session=session)

        # Assert - Verify title was stripped
        statement = select(Todo).where(Todo.title == expected_title)
        db_result = session.exec(statement)
        created_todo = db_result.first()

        assert created_todo is not None
        assert created_todo.title == expected_title
        assert created_todo.title == expected_title.strip()

    def test_create_todo_timestamps_auto_generated(self, session):
        """Test that created_at and updated_at timestamps are auto-generated."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "Test timestamps"
        before_creation = datetime.now(timezone.utc)

        # Act
        result = create_todo(title=title, _test_session=session)

        # Assert
        after_creation = datetime.now(timezone.utc)
        statement = select(Todo).where(Todo.title == title)
        db_result = session.exec(statement)
        created_todo = db_result.first()

        assert created_todo is not None
        assert created_todo.created_at is not None
        assert created_todo.updated_at is not None
        assert before_creation <= created_todo.created_at <= after_creation
        assert before_creation <= created_todo.updated_at <= after_creation
        assert created_todo.created_at == created_todo.updated_at  # Should be identical on creation

    def test_create_todo_returns_mcp_compliant_response(self, session):
        """Test that create_todo returns MCP-compliant Content object."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        title = "Test MCP response"

        # Act
        result = create_todo(title=title, _test_session=session)

        # Assert - FastMCP automatically converts to MCP Content format
        # Tool should return a string (FastMCP handles Content wrapping)
        assert isinstance(result, str)
        assert len(result) > 0
        assert title in result  # Response should mention the created todo

    def test_create_multiple_todos_sequentially(self, session):
        """Test creating multiple todos in sequence generates unique IDs."""
        # Arrange
        from src.mcp_server.tools.create_todo import create_todo

        # Act
        result1 = create_todo(title="First todo")
        result2 = create_todo(title="Second todo")
        result3 = create_todo(title="Third todo")

        # Assert - Verify all todos created with unique IDs
        statement = select(Todo)
        db_result = session.exec(statement)
        all_todos = db_result.all()

        assert len(all_todos) >= 3
        titles = [todo.title for todo in all_todos]
        assert "First todo" in titles
        assert "Second todo" in titles
        assert "Third todo" in titles

        # Verify IDs are unique
        ids = [todo.id for todo in all_todos]
        assert len(ids) == len(set(ids))  # All IDs are unique


class TestListTodosTool:
    """Integration tests for list_todos MCP tool.

    Tests cover:
    - Retrieving all active todos
    - Filtering (exclude completed and archived todos)
    - Empty list handling
    - MCP response format compliance
    - Correct ordering (if applicable)
    """

    def test_list_todos_returns_active_only(self, session, sample_todos):
        """Test that list_todos returns only active todos, excluding completed/archived."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # sample_todos has 2 active, 1 completed, 1 archived

        # Act
        result = list_todos()

        # Assert - Should only return active todos
        assert isinstance(result, str)
        assert "Active Todo 1" in result
        assert "Active Todo 2" in result
        assert "Completed Todo" not in result  # Should be excluded
        assert "Archived Todo" not in result  # Should be excluded

    def test_list_todos_empty_database(self, session):
        """Test that list_todos handles empty database gracefully."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Database is empty (no sample_todos fixture)

        # Act
        result = list_todos()

        # Assert - Should return empty result or message indicating no todos
        assert isinstance(result, str)
        assert "0" in result or "no" in result.lower() or "empty" in result.lower()

    def test_list_todos_with_single_active_todo(self, session, sample_todo):
        """Test list_todos with exactly one active todo."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # sample_todo fixture provides 1 active todo

        # Act
        result = list_todos()

        # Assert
        assert isinstance(result, str)
        assert sample_todo.title in result
        assert "1" in result or "one" in result.lower()  # Should indicate 1 todo

    def test_list_todos_excludes_completed_status(self, session):
        """Test that list_todos excludes todos with completed status."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create active and completed todos
        active_todo = Todo(title="Active task", status=TodoStatus.ACTIVE)
        completed_todo = Todo(title="Completed task", status=TodoStatus.COMPLETED)
        session.add(active_todo)
        session.add(completed_todo)
        session.commit()

        # Act
        result = list_todos()

        # Assert
        assert "Active task" in result
        assert "Completed task" not in result

    def test_list_todos_excludes_archived_status(self, session):
        """Test that list_todos excludes todos with archived status."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create active and archived todos
        active_todo = Todo(title="Active task", status=TodoStatus.ACTIVE)
        archived_todo = Todo(title="Archived task", status=TodoStatus.ARCHIVED)
        session.add(active_todo)
        session.add(archived_todo)
        session.commit()

        # Act
        result = list_todos()

        # Assert
        assert "Active task" in result
        assert "Archived task" not in result

    def test_list_todos_returns_mcp_compliant_response(self, session, sample_todos):
        """Test that list_todos returns MCP-compliant Content object."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Act
        result = list_todos()

        # Assert - FastMCP automatically converts to MCP Content format
        # Tool should return a string (FastMCP handles Content wrapping)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_todos_includes_all_active_fields(self, session):
        """Test that list_todos includes all todo fields (id, title, description, status, timestamps)."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        todo = Todo(
            title="Test todo",
            description="Test description",
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Act
        result = list_todos()

        # Assert - Response should include key fields
        assert "Test todo" in result  # Title
        assert "Test description" in result  # Description
        assert str(todo.id) in result or f"ID: {todo.id}" in result  # ID
        # Note: Timestamps may be formatted differently

    def test_list_todos_with_multiple_active_todos(self, session):
        """Test list_todos returns all active todos when multiple exist."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create 5 active todos
        for i in range(1, 6):
            todo = Todo(title=f"Active todo {i}", status=TodoStatus.ACTIVE)
            session.add(todo)
        session.commit()

        # Act
        result = list_todos()

        # Assert - All 5 should be in result
        assert isinstance(result, str)
        for i in range(1, 6):
            assert f"Active todo {i}" in result

    def test_list_todos_after_status_change_to_completed(self, session):
        """Test that todo disappears from list_todos after status changed to completed."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create active todo
        todo = Todo(title="Task to complete", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Verify it appears in list
        result_before = list_todos()
        assert "Task to complete" in result_before

        # Act - Change status to completed
        todo.status = TodoStatus.COMPLETED
        session.add(todo)
        session.commit()

        # Assert - Should no longer appear in list
        result_after = list_todos()
        assert "Task to complete" not in result_after

    def test_list_todos_after_status_change_to_archived(self, session):
        """Test that todo disappears from list_todos after status changed to archived."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create active todo
        todo = Todo(title="Task to archive", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Verify it appears in list
        result_before = list_todos()
        assert "Task to archive" in result_before

        # Act - Change status to archived
        todo.status = TodoStatus.ARCHIVED
        session.add(todo)
        session.commit()

        # Assert - Should no longer appear in list
        result_after = list_todos()
        assert "Task to archive" not in result_after

    def test_list_todos_count_accuracy(self, session):
        """Test that list_todos count matches actual number of active todos."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create 3 active, 2 completed, 1 archived
        for i in range(3):
            session.add(Todo(title=f"Active {i}", status=TodoStatus.ACTIVE))
        for i in range(2):
            session.add(Todo(title=f"Completed {i}", status=TodoStatus.COMPLETED))
        session.add(Todo(title="Archived", status=TodoStatus.ARCHIVED))
        session.commit()

        # Act
        result = list_todos()

        # Assert - Should report 3 active todos
        assert "3" in result or "three" in result.lower()
        # Verify all active todos present
        for i in range(3):
            assert f"Active {i}" in result
