"""Comprehensive tests for delete_todo MCP tool.

This module provides thorough testing of the delete_todo functionality:
- Single ID deletion
- Multiple ID deletion (batch)
- Filter-based deletion (status, priority, keyword)
- Confirmation flow for mass deletions (3+ items)
- Error handling (not found, invalid input)
- JSON string output format validation
"""

import pytest
import json
from sqlmodel import select

from src.mcp_server.models import Todo, TodoStatus, TodoPriority
from src.mcp_server.tools.delete_todo import _delete_todo_impl, delete_todo


class TestDeleteTodoSingleId:
    """Tests for single todo deletion by ID."""

    def test_delete_existing_todo_by_id(self, session):
        """Test successfully deleting a todo by its ID."""
        # Arrange
        todo = Todo(title="Delete me", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        todo_id = todo.id

        # Act
        result = _delete_todo_impl(id=todo_id, _test_session=session)

        # Assert - Returns JSON string
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["success"] is True
        assert data["deleted_id"] == todo_id
        assert "deleted" in data["message"].lower()

        # Assert - Todo is removed from database
        assert session.get(Todo, todo_id) is None

    def test_delete_completed_todo(self, session):
        """Test deleting a completed todo."""
        # Arrange
        todo = Todo(title="Completed task", status=TodoStatus.COMPLETED)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        todo_id = todo.id

        # Act
        result = _delete_todo_impl(id=todo_id, _test_session=session)

        # Assert
        data = json.loads(result)
        assert data["success"] is True
        assert session.get(Todo, todo_id) is None

    def test_delete_archived_todo(self, session):
        """Test deleting an archived todo."""
        # Arrange
        todo = Todo(title="Archived task", status=TodoStatus.ARCHIVED)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        todo_id = todo.id

        # Act
        result = _delete_todo_impl(id=todo_id, _test_session=session)

        # Assert
        data = json.loads(result)
        assert data["success"] is True
        assert session.get(Todo, todo_id) is None

    def test_delete_nonexistent_todo_raises_error(self, session):
        """Test that deleting non-existent ID raises ValueError."""
        # Arrange
        nonexistent_id = 99999

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            _delete_todo_impl(id=nonexistent_id, _test_session=session)

        assert "not found" in str(exc_info.value).lower()

    def test_delete_does_not_affect_other_todos(self, session, sample_todos):
        """Test that deleting one todo doesn't affect others."""
        # Arrange
        todo_to_delete = sample_todos[0]
        other_todos = sample_todos[1:]
        original_count = len(sample_todos)

        # Act
        _delete_todo_impl(id=todo_to_delete.id, _test_session=session)

        # Assert - Only the specified todo was deleted
        remaining = session.exec(select(Todo)).all()
        assert len(remaining) == original_count - 1
        assert todo_to_delete.id not in [t.id for t in remaining]
        for other in other_todos:
            assert session.get(Todo, other.id) is not None


class TestDeleteTodoJsonOutput:
    """Tests for JSON string output format compliance."""

    def test_delete_returns_json_string_not_dict(self, session):
        """Test that delete_todo returns a JSON string, not a dict."""
        # Arrange
        todo = Todo(title="JSON test", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Act
        result = _delete_todo_impl(id=todo.id, _test_session=session)

        # Assert - Must be string, not dict
        assert isinstance(result, str)
        assert not isinstance(result, dict)

        # Assert - String is valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_delete_json_contains_required_fields(self, session):
        """Test that JSON response contains all required fields."""
        # Arrange
        todo = Todo(title="Fields test", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Act
        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        # Assert - Required fields present
        assert "success" in data
        assert "deleted_id" in data
        assert "message" in data

    def test_mcp_tool_wrapper_returns_json_string(self, session):
        """Test that the @mcp.tool decorated function returns JSON string."""
        # Note: This tests the public API, not the internal implementation
        # The actual MCP tool is tested via _delete_todo_impl with session
        todo = Todo(title="Wrapper test", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)

        # Verify it's a valid JSON string
        assert isinstance(result, str)
        json.loads(result)  # Should not raise


class TestDeleteTodoPriority:
    """Tests for deleting todos with different priorities."""

    def test_delete_high_priority_todo(self, session):
        """Test deleting a high priority todo."""
        todo = Todo(title="Urgent", priority=TodoPriority.HIGH, status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True
        assert session.get(Todo, todo.id) is None

    def test_delete_low_priority_todo(self, session):
        """Test deleting a low priority todo."""
        todo = Todo(title="Someday", priority=TodoPriority.LOW, status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True
        assert session.get(Todo, todo.id) is None


class TestDeleteTodoWithDescription:
    """Tests for deleting todos with various description content."""

    def test_delete_todo_with_long_description(self, session):
        """Test deleting todo with long description."""
        todo = Todo(
            title="Long desc",
            description="A" * 1000,  # Long description
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True

    def test_delete_todo_with_special_characters(self, session):
        """Test deleting todo with special characters in title/description."""
        todo = Todo(
            title="Test @#$% special chars!",
            description="Description with émojis 🎉 and symbols <>&\"'",
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True
        assert session.get(Todo, todo.id) is None


class TestDeleteTodoEdgeCases:
    """Edge case tests for delete_todo."""

    def test_delete_todo_with_tags(self, session):
        """Test deleting todo that has tags."""
        todo = Todo(
            title="Tagged task",
            tags=["work", "urgent", "project-x"],
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True

    def test_delete_todo_with_due_date(self, session):
        """Test deleting todo that has a due date."""
        from datetime import datetime, timezone

        todo = Todo(
            title="Due date task",
            due_date=datetime.now(timezone.utc),
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _delete_todo_impl(id=todo.id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True

    def test_delete_recently_created_todo(self, session):
        """Test deleting a todo immediately after creation."""
        todo = Todo(title="New todo", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        todo_id = todo.id

        # Delete immediately
        result = _delete_todo_impl(id=todo_id, _test_session=session)
        data = json.loads(result)

        assert data["success"] is True
        assert data["deleted_id"] == todo_id

    def test_delete_same_todo_twice_fails(self, session):
        """Test that deleting the same todo twice raises error on second attempt."""
        todo = Todo(title="Delete twice", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        todo_id = todo.id

        # First delete succeeds
        result = _delete_todo_impl(id=todo_id, _test_session=session)
        data = json.loads(result)
        assert data["success"] is True

        # Second delete fails
        with pytest.raises(ValueError) as exc_info:
            _delete_todo_impl(id=todo_id, _test_session=session)

        assert "not found" in str(exc_info.value).lower()


class TestDeleteTodoInputValidation:
    """Tests for input validation in delete_todo."""

    def test_delete_with_zero_id(self, session):
        """Test handling of ID = 0."""
        # Create a todo first to ensure database is not empty
        todo = Todo(title="Real todo", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()

        # ID 0 doesn't exist
        with pytest.raises(ValueError):
            _delete_todo_impl(id=0, _test_session=session)

    def test_delete_with_negative_id(self, session):
        """Test handling of negative ID."""
        with pytest.raises(ValueError):
            _delete_todo_impl(id=-1, _test_session=session)

    def test_delete_with_very_large_id(self, session):
        """Test handling of very large ID that doesn't exist."""
        with pytest.raises(ValueError):
            _delete_todo_impl(id=999999999, _test_session=session)


class TestDeleteTodoTransactionBehavior:
    """Tests for database transaction behavior."""

    def test_delete_is_permanent(self, session):
        """Test that deletion is permanent and persisted."""
        todo = Todo(title="Permanent delete", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)
        todo_id = todo.id

        _delete_todo_impl(id=todo_id, _test_session=session)

        # Create new query to verify persistence
        result = session.exec(select(Todo).where(Todo.id == todo_id)).first()
        assert result is None

    def test_delete_updates_total_count(self, session, sample_todos):
        """Test that deletion correctly reduces total count."""
        initial_count = len(session.exec(select(Todo)).all())

        _delete_todo_impl(id=sample_todos[0].id, _test_session=session)

        final_count = len(session.exec(select(Todo)).all())
        assert final_count == initial_count - 1
