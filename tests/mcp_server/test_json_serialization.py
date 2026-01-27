"""Tests for MCP tool JSON serialization.

This module verifies that all MCP tools return JSON strings (not dicts),
which is required for compatibility with OpenAI function tools.

Critical requirement: OpenAI function tools expect string outputs.
These tests ensure we don't regress to returning dicts.
"""

import pytest
import json
from datetime import datetime, timezone

from src.mcp_server.models import Todo, TodoStatus, TodoPriority


class TestCreateTodoStringSerialization:
    """Tests for create_todo string output format.

    Note: create_todo returns a human-readable string, not JSON.
    This is intentional for better agent response formatting.
    """

    def test_create_todo_returns_string(self, session):
        """Test that create_todo returns a string."""
        from src.mcp_server.tools.create_todo import _create_todo_impl

        result = _create_todo_impl(title="Test todo", _test_session=session)

        assert isinstance(result, str)
        assert not isinstance(result, dict)

    def test_create_todo_contains_success_message(self, session):
        """Test that create_todo response contains success indicator."""
        from src.mcp_server.tools.create_todo import _create_todo_impl

        result = _create_todo_impl(title="Test todo", _test_session=session)

        # Should contain success message or created indicator
        assert "created" in result.lower() or "success" in result.lower()

    def test_create_todo_contains_id(self, session):
        """Test that create_todo response contains the ID."""
        from src.mcp_server.tools.create_todo import _create_todo_impl

        result = _create_todo_impl(title="Test todo", _test_session=session)

        # Should contain ID reference
        assert "ID:" in result or "id:" in result.lower()


class TestListTodosJsonSerialization:
    """Tests for list_todos JSON string output."""

    def test_list_todos_returns_string(self, session):
        """Test that list_todos returns a string, not a dict."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(_test_session=session)

        assert isinstance(result, str)
        assert not isinstance(result, dict)

    def test_list_todos_returns_valid_json(self, session, sample_todos):
        """Test that list_todos returns valid JSON."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(_test_session=session)

        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_list_todos_json_has_todos_array(self, session, sample_todos):
        """Test that list_todos JSON contains 'todos' array."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(_test_session=session)
        parsed = json.loads(result)

        assert "todos" in parsed
        assert isinstance(parsed["todos"], list)

    def test_list_todos_json_has_total(self, session, sample_todos):
        """Test that list_todos JSON contains 'total' count."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(_test_session=session)
        parsed = json.loads(result)

        assert "total" in parsed
        assert isinstance(parsed["total"], int)

    def test_list_todos_json_todo_fields(self, session, sample_todos):
        """Test that list_todos JSON todos have expected fields."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(_test_session=session)
        parsed = json.loads(result)

        if parsed["todos"]:
            todo = parsed["todos"][0]
            assert "id" in todo
            assert "title" in todo
            assert "status" in todo

    def test_list_todos_with_filters_returns_string(self, session, sample_todos_with_priority):
        """Test that list_todos with filters returns JSON string."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(
            status="active",
            priority="high",
            _test_session=session
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


class TestSearchTodosJsonSerialization:
    """Tests for search_todos JSON string output."""

    def test_search_todos_returns_string(self, session, sample_todos):
        """Test that search_todos returns a string, not a dict."""
        from src.mcp_server.tools.search_todos import _search_todos_impl

        result = _search_todos_impl(keyword="Active", _test_session=session)

        assert isinstance(result, str)
        assert not isinstance(result, dict)

    def test_search_todos_returns_valid_json(self, session, sample_todos):
        """Test that search_todos returns valid JSON."""
        from src.mcp_server.tools.search_todos import _search_todos_impl

        result = _search_todos_impl(keyword="Todo", _test_session=session)

        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_search_todos_json_has_todos_array(self, session, sample_todos):
        """Test that search_todos JSON contains 'todos' array."""
        from src.mcp_server.tools.search_todos import _search_todos_impl

        result = _search_todos_impl(keyword="Active", _test_session=session)
        parsed = json.loads(result)

        assert "todos" in parsed
        assert isinstance(parsed["todos"], list)

    def test_search_todos_json_has_query(self, session, sample_todos):
        """Test that search_todos JSON contains 'query' field."""
        from src.mcp_server.tools.search_todos import _search_todos_impl

        result = _search_todos_impl(keyword="Active", _test_session=session)
        parsed = json.loads(result)

        assert "query" in parsed

    def test_search_todos_empty_result_returns_string(self, session):
        """Test that search_todos returns JSON string even for no matches."""
        from src.mcp_server.tools.search_todos import _search_todos_impl

        result = _search_todos_impl(keyword="nonexistent", _test_session=session)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["total"] == 0


class TestDeleteTodoJsonSerialization:
    """Tests for delete_todo JSON string output."""

    def test_delete_todo_returns_string(self, session, sample_todo):
        """Test that delete_todo returns a string, not a dict."""
        from src.mcp_server.tools.delete_todo import _delete_todo_impl

        result = _delete_todo_impl(id=sample_todo.id, _test_session=session)

        assert isinstance(result, str)
        assert not isinstance(result, dict)

    def test_delete_todo_returns_valid_json(self, session, sample_todo):
        """Test that delete_todo returns valid JSON."""
        from src.mcp_server.tools.delete_todo import _delete_todo_impl

        result = _delete_todo_impl(id=sample_todo.id, _test_session=session)

        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_delete_todo_json_has_success(self, session, sample_todo):
        """Test that delete_todo JSON contains 'success' field."""
        from src.mcp_server.tools.delete_todo import _delete_todo_impl

        result = _delete_todo_impl(id=sample_todo.id, _test_session=session)
        parsed = json.loads(result)

        assert "success" in parsed
        assert isinstance(parsed["success"], bool)

    def test_delete_todo_json_has_deleted_id(self, session, sample_todo):
        """Test that delete_todo JSON contains 'deleted_id' field."""
        from src.mcp_server.tools.delete_todo import _delete_todo_impl

        todo_id = sample_todo.id
        result = _delete_todo_impl(id=todo_id, _test_session=session)
        parsed = json.loads(result)

        assert "deleted_id" in parsed
        assert parsed["deleted_id"] == todo_id

    def test_delete_todo_json_has_message(self, session, sample_todo):
        """Test that delete_todo JSON contains 'message' field."""
        from src.mcp_server.tools.delete_todo import _delete_todo_impl

        result = _delete_todo_impl(id=sample_todo.id, _test_session=session)
        parsed = json.loads(result)

        assert "message" in parsed
        assert isinstance(parsed["message"], str)


class TestUpdateTodoStringSerialization:
    """Tests for update_todo string output format.

    Note: update_todo returns a human-readable string, not JSON.
    This is intentional for better agent response formatting.
    """

    def test_update_todo_returns_string(self, session):
        """Test that update_todo returns a string."""
        from src.mcp_server.tools.update_todo import _update_todo_impl

        # Create a todo first
        todo = Todo(title="Original", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _update_todo_impl(
            id=todo.id,
            title="Updated title",
            _test_session=session
        )

        assert isinstance(result, str)
        assert not isinstance(result, dict)

    def test_update_todo_contains_success_message(self, session):
        """Test that update_todo response contains success indicator."""
        from src.mcp_server.tools.update_todo import _update_todo_impl

        # Create a todo first
        todo = Todo(title="Original", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        result = _update_todo_impl(
            id=todo.id,
            title="Updated",
            _test_session=session
        )

        # Should contain success message
        assert "updated" in result.lower() or "success" in result.lower()


class TestJsonDatetimeSerialization:
    """Tests for datetime serialization in JSON responses."""

    def test_list_todos_serializes_datetime(self, session):
        """Test that datetimes in list_todos are properly serialized."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        # Create todo with due_date
        todo = Todo(
            title="Test datetime",
            due_date=datetime.now(timezone.utc),
            status=TodoStatus.ACTIVE
        )
        session.add(todo)
        session.commit()

        result = _list_todos_impl(_test_session=session)

        # Should not raise - datetime should be serialized
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_timestamps_are_iso_format(self, session):
        """Test that timestamps are in ISO format."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        todo = Todo(title="Timestamp test", status=TodoStatus.ACTIVE)
        session.add(todo)
        session.commit()

        result = _list_todos_impl(_test_session=session)
        parsed = json.loads(result)

        if parsed["todos"]:
            todo_data = parsed["todos"][0]
            # created_at should be ISO format string
            if "created_at" in todo_data:
                assert isinstance(todo_data["created_at"], str)
                # Should be parseable as datetime
                datetime.fromisoformat(todo_data["created_at"].replace("Z", "+00:00"))


class TestJsonEnumSerialization:
    """Tests for enum serialization in JSON responses."""

    def test_status_serialized_as_string(self, session, sample_todos):
        """Test that status enum is serialized as string value."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(status="all", _test_session=session)
        parsed = json.loads(result)

        if parsed["todos"]:
            for todo in parsed["todos"]:
                assert isinstance(todo["status"], str)
                assert todo["status"] in ["active", "completed", "archived"]

    def test_priority_serialized_as_string(self, session, sample_todos_with_priority):
        """Test that priority enum is serialized as string value."""
        from src.mcp_server.tools.list_todos import _list_todos_impl

        result = _list_todos_impl(status="all", _test_session=session)
        parsed = json.loads(result)

        if parsed["todos"]:
            for todo in parsed["todos"]:
                assert isinstance(todo["priority"], str)
                assert todo["priority"] in ["low", "medium", "high"]
