"""Database models for Todo management.

This module defines the SQLModel entities used for database persistence.
All models include Pydantic validation and SQLAlchemy ORM capabilities.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TodoStatus(str, Enum):
    """Todo status enumeration.

    Defines the lifecycle states for a todo item:
    - ACTIVE: Default state for new todos (visible in list_todos and search_todos)
    - COMPLETED: Todo is finished (soft delete - excluded from list_todos)
    - ARCHIVED: Long-term storage (excluded from all default queries)
    """
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Todo(SQLModel, table=True):
    """Todo entity for database persistence.

    Represents a single todo/task item with support for CRUD operations
    and status-based lifecycle management.

    Fields:
        id: Unique identifier (auto-increment)
        title: Todo title/summary (required, max 200 chars)
        description: Detailed description (optional, max 2000 chars)
        status: Current lifecycle state (active/completed/archived)
        created_at: Timestamp when todo was created (UTC)
        updated_at: Timestamp of last modification (UTC)
    """

    __tablename__ = "todos"

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Unique todo ID (auto-increment)"
    )

    title: str = Field(
        ...,
        max_length=200,
        min_length=1,
        index=True,
        description="Todo title (required, max 200 chars)"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        index=True,
        description="Todo description (optional, max 2000 chars)"
    )

    status: TodoStatus = Field(
        default=TodoStatus.ACTIVE,
        index=True,
        description="Todo status (active/completed/archived)"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        description="Creation timestamp (UTC)"
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        description="Last update timestamp (UTC)"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Buy groceries",
                "description": "Milk, eggs, bread",
                "status": "active",
                "created_at": "2025-12-29T12:00:00Z",
                "updated_at": "2025-12-29T12:00:00Z"
            }
        }
