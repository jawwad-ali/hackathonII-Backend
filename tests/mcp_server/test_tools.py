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
        result = list_todos(_test_session=session)

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
        result = list_todos(_test_session=session)

        # Assert - Should return empty result or message indicating no todos
        assert isinstance(result, str)
        assert "0" in result or "no" in result.lower() or "empty" in result.lower()

    def test_list_todos_with_single_active_todo(self, session, sample_todo):
        """Test list_todos with exactly one active todo."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # sample_todo fixture provides 1 active todo

        # Act
        result = list_todos(_test_session=session)

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
        result = list_todos(_test_session=session)

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
        result = list_todos(_test_session=session)

        # Assert
        assert "Active task" in result
        assert "Archived task" not in result

    def test_list_todos_returns_mcp_compliant_response(self, session, sample_todos):
        """Test that list_todos returns MCP-compliant Content object."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Act
        result = list_todos(_test_session=session)

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
        result = list_todos(_test_session=session)

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
        result = list_todos(_test_session=session)

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
        result_before = list_todos(_test_session=session)
        assert "Task to complete" in result_before

        # Act - Change status to completed
        todo.status = TodoStatus.COMPLETED
        session.add(todo)
        session.commit()

        # Assert - Should no longer appear in list
        result_after = list_todos(_test_session=session)
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
        result_before = list_todos(_test_session=session)
        assert "Task to archive" in result_before

        # Act - Change status to archived
        todo.status = TodoStatus.ARCHIVED
        session.add(todo)
        session.commit()

        # Assert - Should no longer appear in list
        result_after = list_todos(_test_session=session)
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
        result = list_todos(_test_session=session)

        # Assert - Should report 3 active todos
        assert "3" in result or "three" in result.lower()
        # Verify all active todos present
        for i in range(3):
            assert f"Active {i}" in result


class TestUpdateTodoTool:
    """Integration tests for update_todo MCP tool.

    Tests cover:
    - Partial updates (title only, description only, status only)
    - Multiple field updates simultaneously
    - Status transitions (active → completed → active)
    - "Not found" error handling for non-existent IDs
    - Auto-update of updated_at timestamp
    - MCP response format compliance
    """

    def test_update_todo_title_only(self, session, sample_todo):
        """Test updating only the title of an existing todo."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        original_title = sample_todo.title
        original_description = sample_todo.description
        original_status = sample_todo.status
        original_updated_at = sample_todo.updated_at
        new_title = "Updated title for testing"

        # Act
        result = update_todo(id=sample_todo.id, title=new_title, _test_session=session)

        # Assert - Verify database changes
        session.refresh(sample_todo)
        assert sample_todo.title == new_title
        assert sample_todo.title != original_title
        assert sample_todo.description == original_description  # Unchanged
        assert sample_todo.status == original_status  # Unchanged
        assert sample_todo.updated_at > original_updated_at  # Timestamp updated

        # Assert - Verify MCP response format
        assert isinstance(result, str)
        assert "updated" in result.lower()
        assert new_title in result

    def test_update_todo_description_only(self, session, sample_todo):
        """Test updating only the description of an existing todo."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        original_title = sample_todo.title
        original_description = sample_todo.description
        new_description = "This is the updated description for testing purposes"

        # Act
        result = update_todo(id=sample_todo.id, description=new_description, _test_session=session)

        # Assert - Verify database changes
        session.refresh(sample_todo)
        assert sample_todo.description == new_description
        assert sample_todo.description != original_description
        assert sample_todo.title == original_title  # Unchanged

        # Assert - Verify MCP response format
        assert isinstance(result, str)
        assert "updated" in result.lower()

    def test_update_todo_status_only(self, session, sample_todo):
        """Test updating only the status of an existing todo."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        original_title = sample_todo.title
        original_description = sample_todo.description
        assert sample_todo.status == TodoStatus.ACTIVE
        new_status = "completed"

        # Act
        result = update_todo(id=sample_todo.id, status=new_status, _test_session=session)

        # Assert - Verify database changes
        session.refresh(sample_todo)
        assert sample_todo.status == TodoStatus.COMPLETED
        assert sample_todo.title == original_title  # Unchanged
        assert sample_todo.description == original_description  # Unchanged

        # Assert - Verify MCP response format
        assert isinstance(result, str)
        assert "updated" in result.lower()

    def test_update_todo_multiple_fields(self, session, sample_todo):
        """Test updating multiple fields simultaneously."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        new_title = "Completely new title"
        new_description = "Completely new description"
        new_status = "completed"

        # Act
        result = update_todo(
            id=sample_todo.id,
            title=new_title,
            description=new_description,
            status=new_status,
            _test_session=session
        )

        # Assert - Verify all fields updated
        session.refresh(sample_todo)
        assert sample_todo.title == new_title
        assert sample_todo.description == new_description
        assert sample_todo.status == TodoStatus.COMPLETED

        # Assert - Verify MCP response format
        assert isinstance(result, str)
        assert "updated" in result.lower()

    def test_update_todo_status_active_to_completed(self, session):
        """Test status transition from active to completed."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        todo = Todo(title="Task to complete", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        assert todo.status == TodoStatus.ACTIVE

        # Act
        result = update_todo(id=todo.id, status="completed", _test_session=session)

        # Assert
        session.refresh(todo)
        assert todo.status == TodoStatus.COMPLETED

    def test_update_todo_status_completed_to_active(self, session):
        """Test reactivating a completed todo (status transition from completed to active)."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        todo = Todo(title="Completed task", status=TodoStatus.COMPLETED)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        assert todo.status == TodoStatus.COMPLETED

        # Act - Reactivate
        result = update_todo(id=todo.id, status="active", _test_session=session)

        # Assert
        session.refresh(todo)
        assert todo.status == TodoStatus.ACTIVE

    def test_update_todo_status_active_to_archived(self, session):
        """Test status transition from active to archived."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        todo = Todo(title="Task to archive", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Act
        result = update_todo(id=todo.id, status="archived", _test_session=session)

        # Assert
        session.refresh(todo)
        assert todo.status == TodoStatus.ARCHIVED

    def test_update_todo_not_found_error(self, session):
        """Test that updating non-existent todo ID raises appropriate error."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        non_existent_id = 99999

        # Act & Assert - Should raise ValueError or similar
        with pytest.raises(Exception) as exc_info:
            update_todo(id=non_existent_id, title="New title", _test_session=session)

        # Verify error message mentions "not found" or similar
        error_message = str(exc_info.value).lower()
        assert "not found" in error_message or "does not exist" in error_message or "not exist" in error_message

    def test_update_todo_updated_at_auto_update(self, session, sample_todo):
        """Test that updated_at timestamp is automatically updated on modification."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        original_updated_at = sample_todo.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        # Act
        result = update_todo(id=sample_todo.id, title="Modified title", _test_session=session)

        # Assert
        session.refresh(sample_todo)
        assert sample_todo.updated_at > original_updated_at

    def test_update_todo_created_at_immutable(self, session, sample_todo):
        """Test that created_at timestamp remains unchanged after update."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        original_created_at = sample_todo.created_at

        # Act
        result = update_todo(id=sample_todo.id, title="Modified title", _test_session=session)

        # Assert
        session.refresh(sample_todo)
        assert sample_todo.created_at == original_created_at

    def test_update_todo_empty_title_validation(self, session, sample_todo):
        """Test that empty title raises validation error."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            update_todo(id=sample_todo.id, title="", _test_session=session)

        # Verify error mentions validation or empty
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "empty" in error_message or "required" in error_message

    def test_update_todo_title_exceeds_max_length(self, session, sample_todo):
        """Test that title exceeding 200 chars raises validation error."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        invalid_title = "A" * 201  # Exceeds max length

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            update_todo(id=sample_todo.id, title=invalid_title, _test_session=session)

        # Verify error mentions validation or length
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "length" in error_message or "max" in error_message

    def test_update_todo_description_exceeds_max_length(self, session, sample_todo):
        """Test that description exceeding 2000 chars raises validation error."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        invalid_description = "A" * 2001  # Exceeds max length

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            update_todo(id=sample_todo.id, description=invalid_description, _test_session=session)

        # Verify error mentions validation or length
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "length" in error_message or "max" in error_message

    def test_update_todo_invalid_status(self, session, sample_todo):
        """Test that invalid status value raises validation error."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            update_todo(id=sample_todo.id, status="invalid_status", _test_session=session)

        # Verify error mentions validation or status
        error_message = str(exc_info.value).lower()
        assert "validation" in error_message or "status" in error_message or "enum" in error_message

    def test_update_todo_returns_mcp_compliant_response(self, session, sample_todo):
        """Test that update_todo returns MCP-compliant Content object."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        # Act
        result = update_todo(id=sample_todo.id, title="New title", _test_session=session)

        # Assert - FastMCP automatically converts to MCP Content format
        assert isinstance(result, str)
        assert len(result) > 0
        assert "updated" in result.lower()

    def test_update_todo_state_transition_cycle_active_completed_active(self, session):
        """Test complete state transition cycle: active → completed → active.

        This test verifies that a todo can be:
        1. Created as active
        2. Marked as completed (soft delete)
        3. Reactivated back to active

        All data should be preserved throughout the cycle, and the todo should
        behave correctly at each stage (e.g., excluded from list_todos when completed,
        re-included when reactivated).
        """
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo
        from src.mcp_server.tools.list_todos import list_todos

        # Create an active todo
        todo = Todo(
            title="Test state transition cycle",
            description="This todo will go through active → completed → active",
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Capture original data for verification
        original_id = todo.id
        original_title = todo.title
        original_description = todo.description
        original_created_at = todo.created_at

        # Verify initial state: active
        assert todo.status == TodoStatus.ACTIVE

        # Verify todo appears in list_todos (active todos only)
        list_result_1 = list_todos(_test_session=session)
        assert original_title in list_result_1

        # Act 1: Transition from active → completed
        result_1 = update_todo(id=todo.id, status="completed", _test_session=session)

        # Assert 1: Verify completion
        session.refresh(todo)
        assert todo.status == TodoStatus.COMPLETED
        assert "updated" in result_1.lower()

        # Verify todo is now excluded from list_todos (soft delete behavior)
        list_result_2 = list_todos(_test_session=session)
        assert original_title not in list_result_2

        # Verify all other data preserved
        assert todo.id == original_id
        assert todo.title == original_title
        assert todo.description == original_description
        assert todo.created_at == original_created_at
        assert todo.updated_at > original_created_at  # Timestamp updated

        # Capture updated_at after first transition
        updated_at_after_completion = todo.updated_at

        # Act 2: Transition from completed → active (reactivation)
        result_2 = update_todo(id=todo.id, status="active", _test_session=session)

        # Assert 2: Verify reactivation
        session.refresh(todo)
        assert todo.status == TodoStatus.ACTIVE
        assert "updated" in result_2.lower()

        # Verify todo is now re-included in list_todos
        list_result_3 = list_todos(_test_session=session)
        assert original_title in list_result_3

        # Verify all data still preserved
        assert todo.id == original_id
        assert todo.title == original_title
        assert todo.description == original_description
        assert todo.created_at == original_created_at
        assert todo.updated_at > updated_at_after_completion  # Timestamp updated again

        # Final verification: full cycle completed successfully
        assert todo.status == TodoStatus.ACTIVE  # Back to original state
        assert todo.id == original_id  # Same ID throughout
        assert todo.created_at == original_created_at  # Created timestamp immutable


class TestSoftDeleteBehavior:
    """Integration tests for soft delete behavior (status-based filtering).

    Tests verify that completed and archived todos are properly excluded
    from list_todos results, implementing soft delete functionality.
    """

    def test_completed_todo_excluded_from_list_todos(self, session):
        """Test that completed todos do not appear in list_todos results."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create active and completed todos
        active_todo = Todo(title="Active task", status=TodoStatus.ACTIVE)
        completed_todo = Todo(title="Completed task", status=TodoStatus.COMPLETED)
        session.add(active_todo)
        session.add(completed_todo)
        session.commit()

        # Act
        result = list_todos(_test_session=session)

        # Assert - Only active todo appears
        assert "Active task" in result
        assert "Completed task" not in result

    def test_archived_todo_excluded_from_list_todos(self, session):
        """Test that archived todos do not appear in list_todos results."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos

        # Create active and archived todos
        active_todo = Todo(title="Active task", status=TodoStatus.ACTIVE)
        archived_todo = Todo(title="Archived task", status=TodoStatus.ARCHIVED)
        session.add(active_todo)
        session.add(archived_todo)
        session.commit()

        # Act
        result = list_todos(_test_session=session)

        # Assert - Only active todo appears
        assert "Active task" in result
        assert "Archived task" not in result

    def test_soft_delete_via_status_change_to_completed(self, session):
        """Test soft delete by changing status to completed (todo disappears from list)."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos
        from src.mcp_server.tools.update_todo import update_todo

        # Create active todo
        todo = Todo(title="Task to soft delete", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Verify it appears in list
        result_before = list_todos(_test_session=session)
        assert "Task to soft delete" in result_before

        # Act - Soft delete by changing status to completed
        update_todo(id=todo.id, status="completed", _test_session=session)

        # Assert - Todo no longer appears in list_todos
        result_after = list_todos(_test_session=session)
        assert "Task to soft delete" not in result_after

        # Verify todo still exists in database (soft delete, not hard delete)
        session.refresh(todo)
        assert todo.id is not None
        assert todo.status == TodoStatus.COMPLETED

    def test_soft_delete_via_status_change_to_archived(self, session):
        """Test soft delete by changing status to archived (todo disappears from list)."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos
        from src.mcp_server.tools.update_todo import update_todo

        # Create active todo
        todo = Todo(title="Task to archive", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Verify it appears in list
        result_before = list_todos(_test_session=session)
        assert "Task to archive" in result_before

        # Act - Soft delete by changing status to archived
        update_todo(id=todo.id, status="archived", _test_session=session)

        # Assert - Todo no longer appears in list_todos
        result_after = list_todos(_test_session=session)
        assert "Task to archive" not in result_after

        # Verify todo still exists in database
        session.refresh(todo)
        assert todo.id is not None
        assert todo.status == TodoStatus.ARCHIVED

    def test_reactivate_completed_todo(self, session):
        """Test that completed todo can be reactivated and re-appears in list_todos."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos
        from src.mcp_server.tools.update_todo import update_todo

        # Create completed todo
        todo = Todo(title="Completed task", status=TodoStatus.COMPLETED)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Verify it does NOT appear in list
        result_before = list_todos(_test_session=session)
        assert "Completed task" not in result_before

        # Act - Reactivate by changing status back to active
        update_todo(id=todo.id, status="active", _test_session=session)

        # Assert - Todo re-appears in list_todos
        result_after = list_todos(_test_session=session)
        assert "Completed task" in result_after

        # Verify status changed in database
        session.refresh(todo)
        assert todo.status == TodoStatus.ACTIVE

    def test_reactivate_archived_todo(self, session):
        """Test that archived todo can be reactivated and re-appears in list_todos."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos
        from src.mcp_server.tools.update_todo import update_todo

        # Create archived todo
        todo = Todo(title="Archived task", status=TodoStatus.ARCHIVED)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Verify it does NOT appear in list
        result_before = list_todos(_test_session=session)
        assert "Archived task" not in result_before

        # Act - Reactivate
        update_todo(id=todo.id, status="active", _test_session=session)

        # Assert - Todo re-appears in list_todos
        result_after = list_todos(_test_session=session)
        assert "Archived task" in result_after

        # Verify status changed
        session.refresh(todo)
        assert todo.status == TodoStatus.ACTIVE

    def test_multiple_soft_deletes(self, session):
        """Test multiple todos can be soft deleted independently."""
        # Arrange
        from src.mcp_server.tools.list_todos import list_todos
        from src.mcp_server.tools.update_todo import update_todo

        # Create multiple active todos
        todo1 = Todo(title="Task 1", status=TodoStatus.ACTIVE)
        todo2 = Todo(title="Task 2", status=TodoStatus.ACTIVE)
        todo3 = Todo(title="Task 3", status=TodoStatus.ACTIVE)
        session.add_all([todo1, todo2, todo3])
        session.commit()
        for todo in [todo1, todo2, todo3]:
            session.refresh(todo)

        # Verify all appear in list
        result_initial = list_todos(_test_session=session)
        assert "Task 1" in result_initial
        assert "Task 2" in result_initial
        assert "Task 3" in result_initial

        # Act - Soft delete task 1 and task 3
        update_todo(id=todo1.id, status="completed", _test_session=session)
        update_todo(id=todo3.id, status="archived", _test_session=session)

        # Assert - Only task 2 remains in list
        result_after = list_todos(_test_session=session)
        assert "Task 1" not in result_after
        assert "Task 2" in result_after
        assert "Task 3" not in result_after

    def test_soft_delete_preserves_data(self, session):
        """Test that soft delete preserves all todo data (title, description, timestamps)."""
        # Arrange
        from src.mcp_server.tools.update_todo import update_todo

        todo = Todo(
            title="Important task",
            description="Critical details that must be preserved",
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Capture original data
        original_id = todo.id
        original_title = todo.title
        original_description = todo.description
        original_created_at = todo.created_at

        # Act - Soft delete
        update_todo(id=todo.id, status="completed", _test_session=session)

        # Assert - All data preserved except status
        session.refresh(todo)
        assert todo.id == original_id
        assert todo.title == original_title
        assert todo.description == original_description
        assert todo.created_at == original_created_at
        assert todo.status == TodoStatus.COMPLETED


class TestSearchTodosTool:
    """Integration tests for search_todos MCP tool.

    Tests cover:
    - Keyword matching in title field
    - Keyword matching in description field
    - Status filtering (only active todos returned)
    - Case-insensitive search
    - Empty results when no matches found
    - MCP response format compliance
    """

    def test_search_todos_keyword_matching_in_title(self, session):
        """Test searching for todos by keyword in title field.

        Verifies that search_todos correctly matches keywords in todo titles
        and returns only active todos with matching titles.
        """
        # Arrange
        from src.mcp_server.tools.search_todos import search_todos

        # Create todos with different titles
        todo1 = Todo(title="Buy groceries", description="Milk and eggs", status=TodoStatus.ACTIVE)
        todo2 = Todo(title="Call dentist", description="Schedule appointment", status=TodoStatus.ACTIVE)
        todo3 = Todo(title="Buy birthday gift", description="For mom", status=TodoStatus.ACTIVE)
        todo4 = Todo(title="Finish report", description="Q4 report", status=TodoStatus.ACTIVE)

        session.add_all([todo1, todo2, todo3, todo4])
        session.commit()

        # Act - Search for keyword "buy"
        result = search_todos(keyword="buy", _test_session=session)

        # Assert - Only todos with "buy" in title are returned
        assert isinstance(result, str)
        assert "Buy groceries" in result
        assert "Buy birthday gift" in result
        assert "Call dentist" not in result
        assert "Finish report" not in result

        # Verify result mentions the count
        assert "2" in result or "two" in result.lower()

    def test_search_todos_keyword_matching_in_description(self, session):
        """Test searching for todos by keyword in description field.

        Verifies that search_todos correctly matches keywords in todo descriptions
        and returns todos even when keyword is only in description (not title).
        """
        # Arrange
        from src.mcp_server.tools.search_todos import search_todos

        # Create todos with different descriptions
        todo1 = Todo(
            title="Shopping",
            description="Buy milk, bread, and eggs from grocery store",
            status=TodoStatus.ACTIVE
        )
        todo2 = Todo(
            title="Appointment",
            description="Doctor appointment at 3pm",
            status=TodoStatus.ACTIVE
        )
        todo3 = Todo(
            title="Meeting",
            description="Team meeting about grocery delivery project",
            status=TodoStatus.ACTIVE
        )
        todo4 = Todo(
            title="Review",
            description="Review code changes",
            status=TodoStatus.ACTIVE
        )

        session.add_all([todo1, todo2, todo3, todo4])
        session.commit()

        # Act - Search for keyword "grocery" (appears in descriptions only)
        result = search_todos(keyword="grocery", _test_session=session)

        # Assert - Todos with "grocery" in description are returned
        assert isinstance(result, str)
        assert "Shopping" in result  # Has "grocery" in description
        assert "Meeting" in result   # Has "grocery" in description
        assert "Appointment" not in result
        assert "Review" not in result

        # Verify result mentions the count
        assert "2" in result or "two" in result.lower()

    def test_search_todos_excludes_completed_and_archived(self, session):
        """Test that search_todos only returns active todos.

        Verifies that completed and archived todos are excluded from search results,
        even if they match the search keyword.
        """
        # Arrange
        from src.mcp_server.tools.search_todos import search_todos

        # Create todos with same keyword but different statuses
        active_todo = Todo(
            title="Buy groceries",
            description="Active task",
            status=TodoStatus.ACTIVE
        )
        completed_todo = Todo(
            title="Buy supplies",
            description="Completed task",
            status=TodoStatus.COMPLETED
        )
        archived_todo = Todo(
            title="Buy equipment",
            description="Archived task",
            status=TodoStatus.ARCHIVED
        )

        session.add_all([active_todo, completed_todo, archived_todo])
        session.commit()

        # Act - Search for keyword "buy" (all todos have it in title)
        result = search_todos(keyword="buy", _test_session=session)

        # Assert - Only active todo is returned
        assert isinstance(result, str)
        assert "Buy groceries" in result  # Active
        assert "Buy supplies" not in result  # Completed - excluded
        assert "Buy equipment" not in result  # Archived - excluded

        # Verify only 1 result
        assert "1" in result or "one" in result.lower()

    def test_search_todos_case_insensitive_and_empty_results(self, session):
        """Test case-insensitive search and empty results handling.

        Verifies that:
        1. Search is case-insensitive (matches regardless of case)
        2. Empty results are handled gracefully when no matches found
        """
        # Arrange
        from src.mcp_server.tools.search_todos import search_todos

        # Create todos with mixed case
        todo1 = Todo(title="URGENT Meeting", description="Board meeting", status=TodoStatus.ACTIVE)
        todo2 = Todo(title="urgent call", description="Call client", status=TodoStatus.ACTIVE)
        todo3 = Todo(title="Review Report", description="Urgent review needed", status=TodoStatus.ACTIVE)

        session.add_all([todo1, todo2, todo3])
        session.commit()

        # Act 1 - Search with lowercase (should match URGENT, urgent, Urgent)
        result_lowercase = search_todos(keyword="urgent", _test_session=session)

        # Assert 1 - Case-insensitive matching works
        assert isinstance(result_lowercase, str)
        assert "URGENT Meeting" in result_lowercase
        assert "urgent call" in result_lowercase
        assert "Review Report" in result_lowercase  # Has "Urgent" in description

        # Verify all 3 todos found
        assert "3" in result_lowercase or "three" in result_lowercase.lower()

        # Act 2 - Search with uppercase (should also match all)
        result_uppercase = search_todos(keyword="URGENT", _test_session=session)

        # Assert 2 - Case-insensitive matching works both ways
        assert "URGENT Meeting" in result_uppercase
        assert "urgent call" in result_uppercase
        assert "Review Report" in result_uppercase

        # Act 3 - Search for non-existent keyword
        result_empty = search_todos(keyword="nonexistent", _test_session=session)

        # Assert 3 - Empty results handled gracefully
        assert isinstance(result_empty, str)
        assert "0" in result_empty or "no" in result_empty.lower() or "not found" in result_empty.lower()
        assert "URGENT Meeting" not in result_empty
        assert "urgent call" not in result_empty
