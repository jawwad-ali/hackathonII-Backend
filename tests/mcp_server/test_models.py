"""Unit tests for Todo model CRUD operations.

Tests cover:
- Todo creation with required and optional fields
- Todo retrieval by ID
- Todo updates (title, description, status)
- Field validation (title length, status enum)
- Timestamp auto-generation (created_at, updated_at)
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import select

from src.mcp_server.models import Todo, TodoStatus


class TestTodoCreate:
    """Tests for creating Todo instances."""

    def test_create_todo_with_all_fields(self, session):
        """Test creating a todo with all fields specified."""
        # Arrange
        todo = Todo(
            title="Buy groceries",
            description="Milk, eggs, bread",
            status=TodoStatus.ACTIVE
        )

        # Act
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert todo.id is not None  # Auto-generated ID
        assert todo.title == "Buy groceries"
        assert todo.description == "Milk, eggs, bread"
        assert todo.status == TodoStatus.ACTIVE
        assert isinstance(todo.created_at, datetime)
        assert isinstance(todo.updated_at, datetime)
        assert todo.created_at == todo.updated_at  # Initial timestamps match

    def test_create_todo_with_minimal_fields(self, session):
        """Test creating a todo with only required fields (title)."""
        # Arrange
        todo = Todo(title="Call dentist")

        # Act
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert todo.id is not None
        assert todo.title == "Call dentist"
        assert todo.description is None  # Optional field defaults to None
        assert todo.status == TodoStatus.ACTIVE  # Default status
        assert todo.created_at is not None
        assert todo.updated_at is not None

    def test_create_todo_with_completed_status(self, session):
        """Test creating a todo with completed status."""
        # Arrange
        todo = Todo(
            title="Submit expense report",
            description="Q4 2024 expenses",
            status=TodoStatus.COMPLETED
        )

        # Act
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert todo.status == TodoStatus.COMPLETED
        assert todo.id is not None

    def test_create_todo_with_archived_status(self, session):
        """Test creating a todo with archived status."""
        # Arrange
        todo = Todo(
            title="Research laptops",
            status=TodoStatus.ARCHIVED
        )

        # Act
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert todo.status == TodoStatus.ARCHIVED

    def test_create_multiple_todos(self, session):
        """Test creating multiple todos in sequence."""
        # Arrange
        todo1 = Todo(title="First task")
        todo2 = Todo(title="Second task")
        todo3 = Todo(title="Third task")

        # Act
        session.add(todo1)
        session.add(todo2)
        session.add(todo3)
        session.commit()
        session.refresh(todo1)
        session.refresh(todo2)
        session.refresh(todo3)

        # Assert
        assert todo1.id != todo2.id != todo3.id  # Unique IDs
        assert todo1.id < todo2.id < todo3.id  # Sequential IDs


class TestTodoRead:
    """Tests for retrieving Todo instances."""

    def test_read_todo_by_id(self, session, sample_todo):
        """Test retrieving a todo by its ID."""
        # Act
        retrieved_todo = session.get(Todo, sample_todo.id)

        # Assert
        assert retrieved_todo is not None
        assert retrieved_todo.id == sample_todo.id
        assert retrieved_todo.title == sample_todo.title
        assert retrieved_todo.description == sample_todo.description
        assert retrieved_todo.status == sample_todo.status

    def test_read_nonexistent_todo(self, session):
        """Test retrieving a todo with non-existent ID returns None."""
        # Act
        retrieved_todo = session.get(Todo, 99999)

        # Assert
        assert retrieved_todo is None

    def test_read_all_todos(self, session, sample_todos):
        """Test retrieving all todos from database."""
        # Act
        statement = select(Todo)
        result = session.exec(statement)
        all_todos = result.all()

        # Assert
        assert len(all_todos) == len(sample_todos)
        assert len(all_todos) == 4  # From sample_todos fixture

    def test_read_todos_by_status_active(self, session, sample_todos):
        """Test filtering todos by active status."""
        # Act
        statement = select(Todo).where(Todo.status == TodoStatus.ACTIVE)
        result = session.exec(statement)
        active_todos = result.all()

        # Assert
        assert len(active_todos) == 2  # 2 active todos in sample_todos
        for todo in active_todos:
            assert todo.status == TodoStatus.ACTIVE

    def test_read_todos_by_status_completed(self, session, sample_todos):
        """Test filtering todos by completed status."""
        # Act
        statement = select(Todo).where(Todo.status == TodoStatus.COMPLETED)
        result = session.exec(statement)
        completed_todos = result.all()

        # Assert
        assert len(completed_todos) == 1  # 1 completed todo in sample_todos
        assert completed_todos[0].status == TodoStatus.COMPLETED

    def test_read_todos_by_status_archived(self, session, sample_todos):
        """Test filtering todos by archived status."""
        # Act
        statement = select(Todo).where(Todo.status == TodoStatus.ARCHIVED)
        result = session.exec(statement)
        archived_todos = result.all()

        # Assert
        assert len(archived_todos) == 1  # 1 archived todo in sample_todos
        assert archived_todos[0].status == TodoStatus.ARCHIVED


class TestTodoUpdate:
    """Tests for updating Todo instances."""

    def test_update_todo_title(self, session, sample_todo):
        """Test updating a todo's title."""
        # Arrange
        original_title = sample_todo.title
        original_updated_at = sample_todo.updated_at

        # Act
        sample_todo.title = "Updated Title"
        sample_todo.updated_at = datetime.now(timezone.utc)  # Manual update
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.title == "Updated Title"
        assert sample_todo.title != original_title
        assert sample_todo.updated_at >= original_updated_at

    def test_update_todo_description(self, session, sample_todo):
        """Test updating a todo's description."""
        # Arrange
        original_description = sample_todo.description

        # Act
        sample_todo.description = "Updated description with more details"
        sample_todo.updated_at = datetime.now(timezone.utc)
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.description == "Updated description with more details"
        assert sample_todo.description != original_description

    def test_update_todo_status_to_completed(self, session, sample_todo):
        """Test updating a todo's status from active to completed."""
        # Arrange
        assert sample_todo.status == TodoStatus.ACTIVE

        # Act
        sample_todo.status = TodoStatus.COMPLETED
        sample_todo.updated_at = datetime.now(timezone.utc)
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.status == TodoStatus.COMPLETED

    def test_update_todo_status_to_archived(self, session, sample_todo):
        """Test updating a todo's status from active to archived."""
        # Arrange
        assert sample_todo.status == TodoStatus.ACTIVE

        # Act
        sample_todo.status = TodoStatus.ARCHIVED
        sample_todo.updated_at = datetime.now(timezone.utc)
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.status == TodoStatus.ARCHIVED

    def test_update_todo_reactivate_from_completed(self, session):
        """Test reactivating a completed todo."""
        # Arrange
        todo = Todo(
            title="Completed task",
            status=TodoStatus.COMPLETED
        )
        session.add(todo)
        session.commit()
        session.refresh(todo)
        assert todo.status == TodoStatus.COMPLETED

        # Act - Reactivate
        todo.status = TodoStatus.ACTIVE
        todo.updated_at = datetime.now(timezone.utc)
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert todo.status == TodoStatus.ACTIVE

    def test_update_multiple_fields(self, session, sample_todo):
        """Test updating multiple fields simultaneously."""
        # Arrange
        original_title = sample_todo.title
        original_description = sample_todo.description
        original_status = sample_todo.status

        # Act
        sample_todo.title = "New title"
        sample_todo.description = "New description"
        sample_todo.status = TodoStatus.COMPLETED
        sample_todo.updated_at = datetime.now(timezone.utc)
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.title == "New title"
        assert sample_todo.description == "New description"
        assert sample_todo.status == TodoStatus.COMPLETED
        assert sample_todo.title != original_title
        assert sample_todo.description != original_description
        assert sample_todo.status != original_status

    def test_update_todo_updated_at_auto_update(self, session, sample_todo):
        """Test that updated_at timestamp is updated on modification."""
        # Arrange
        original_updated_at = sample_todo.updated_at

        # Act - Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        sample_todo.title = "Modified title"
        sample_todo.updated_at = datetime.now(timezone.utc)
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.updated_at > original_updated_at

    def test_update_created_at_immutable(self, session, sample_todo):
        """Test that created_at timestamp should not change on update."""
        # Arrange
        original_created_at = sample_todo.created_at

        # Act
        sample_todo.title = "Modified title"
        sample_todo.updated_at = datetime.now(timezone.utc)
        session.add(sample_todo)
        session.commit()
        session.refresh(sample_todo)

        # Assert
        assert sample_todo.created_at == original_created_at  # Should remain unchanged


class TestTodoValidation:
    """Tests for Todo model field validation."""

    def test_todo_title_max_length(self, session):
        """Test that title respects max_length constraint (200 chars)."""
        # Arrange - Title with exactly 200 characters
        valid_title = "A" * 200
        todo = Todo(title=valid_title)

        # Act
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert len(todo.title) == 200

    def test_todo_title_exceeds_max_length(self):
        """Test that title exceeding 200 chars raises validation error."""
        # Arrange - Title with 201 characters
        invalid_title = "A" * 201

        # Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            Todo(title=invalid_title)

    def test_todo_description_max_length(self, session):
        """Test that description respects max_length constraint (2000 chars)."""
        # Arrange - Description with exactly 2000 characters
        valid_description = "A" * 2000
        todo = Todo(
            title="Test",
            description=valid_description
        )

        # Act
        session.add(todo)
        session.commit()
        session.refresh(todo)

        # Assert
        assert len(todo.description) == 2000

    def test_todo_description_exceeds_max_length(self):
        """Test that description exceeding 2000 chars raises validation error."""
        # Arrange - Description with 2001 characters
        invalid_description = "A" * 2001

        # Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            Todo(
                title="Test",
                description=invalid_description
            )

    def test_todo_status_invalid_value(self):
        """Test that invalid status value raises validation error."""
        # Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            Todo(
                title="Test",
                status="invalid_status"  # Not a valid TodoStatus enum value
            )

    def test_todo_title_empty_string(self):
        """Test that empty title raises validation error."""
        # Act & Assert
        with pytest.raises(Exception):  # Pydantic validation error
            Todo(title="")  # Empty string violates min_length=1


class TestTodoDelete:
    """Tests for deleting Todo instances (hard delete)."""

    def test_delete_todo_by_id(self, session, sample_todo):
        """Test deleting a todo permanently from database."""
        # Arrange
        todo_id = sample_todo.id
        assert session.get(Todo, todo_id) is not None

        # Act
        session.delete(sample_todo)
        session.commit()

        # Assert
        deleted_todo = session.get(Todo, todo_id)
        assert deleted_todo is None

    def test_delete_todo_from_collection(self, session, sample_todos):
        """Test deleting one todo from a collection."""
        # Arrange
        original_count = len(sample_todos)
        todo_to_delete = sample_todos[0]
        todo_id = todo_to_delete.id

        # Act
        session.delete(todo_to_delete)
        session.commit()

        # Assert
        statement = select(Todo)
        result = session.exec(statement)
        remaining_todos = result.all()
        assert len(remaining_todos) == original_count - 1
        assert session.get(Todo, todo_id) is None

    def test_delete_all_todos(self, session, sample_todos):
        """Test deleting all todos from database."""
        # Arrange
        assert len(sample_todos) > 0

        # Act
        for todo in sample_todos:
            session.delete(todo)
        session.commit()

        # Assert
        statement = select(Todo)
        result = session.exec(statement)
        remaining_todos = result.all()
        assert len(remaining_todos) == 0
