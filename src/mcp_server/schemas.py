"""Pydantic validation schemas for MCP tool inputs.

This module defines input validation schemas for all MCP tools.
These schemas provide type safety, validation, and clear error messages
for tool callers.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from .models import TodoStatus, TodoPriority


class CreateTodoInput(BaseModel):
    """Input schema for create_todo tool.

    Validates todo creation requests with field-level constraints
    and custom validation logic.

    Attributes:
        title: Todo title (required, 1-200 chars after stripping whitespace)
        description: Optional description (max 2000 chars)
        due_date: Optional due date/time (ISO 8601 datetime string)
        priority: Priority level (low/medium/high, default: medium)
        tags: Optional list of category tags
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Todo title (required, max 200 chars)"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional todo description (max 2000 chars)"
    )

    due_date: Optional[datetime] = Field(
        default=None,
        description="Optional due date/time (ISO 8601 datetime string, UTC)"
    )

    priority: TodoPriority = Field(
        default=TodoPriority.MEDIUM,
        description="Priority level: low, medium (default), or high"
    )

    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional list of category tags (e.g., ['work', 'urgent'])"
    )

    @field_validator("title", mode="after")
    @classmethod
    def validate_title_not_empty(cls, value: str) -> str:
        """Ensure title is not empty or whitespace-only after stripping.

        Args:
            value: The title string to validate

        Returns:
            str: The stripped title value

        Raises:
            ValueError: If title is empty or whitespace-only after stripping
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty or whitespace-only")
        return stripped

    @field_validator("tags", mode="after")
    @classmethod
    def validate_tags_not_empty(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure tags list doesn't contain empty strings and normalize tag values.

        Args:
            value: The tags list to validate (or None)

        Returns:
            Optional[List[str]]: Validated and normalized tags list or None

        Raises:
            ValueError: If any tag is empty or whitespace-only
        """
        if value is None:
            return None

        # Strip whitespace from each tag and validate
        normalized_tags = []
        for tag in value:
            if not isinstance(tag, str):
                raise ValueError(f"Tag must be a string, got {type(tag).__name__}")

            stripped_tag = tag.strip().lower()  # Normalize to lowercase
            if not stripped_tag:
                raise ValueError("Tags cannot be empty or whitespace-only")

            normalized_tags.append(stripped_tag)

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in normalized_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags if unique_tags else None

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "title": "Buy groceries",
                "description": "Milk, eggs, bread, and coffee",
                "due_date": "2025-12-30T15:00:00Z",
                "priority": "medium",
                "tags": ["shopping", "personal"]
            }
        }


class UpdateTodoInput(BaseModel):
    """Input schema for update_todo tool.

    Validates todo update requests with partial update support.
    At least one field (title, description, or status) must be provided.

    Attributes:
        id: Todo ID to update (required)
        title: New title (optional, 1-200 chars after stripping)
        description: New description (optional, max 2000 chars)
        status: New status (optional, must be valid TodoStatus)
    """

    id: int = Field(
        ...,
        gt=0,
        description="Todo ID to update (must be positive integer)"
    )

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="New title (optional, max 200 chars)"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="New description (optional, max 2000 chars)"
    )

    status: Optional[TodoStatus] = Field(
        default=None,
        description="New status (optional: active, completed, archived)"
    )

    @field_validator("title", mode="after")
    @classmethod
    def validate_title_not_empty(cls, value: Optional[str]) -> Optional[str]:
        """Ensure title is not empty or whitespace-only if provided.

        Args:
            value: The title string to validate (or None)

        Returns:
            Optional[str]: The stripped title value or None

        Raises:
            ValueError: If title is provided but empty/whitespace-only after stripping
        """
        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty or whitespace-only")
        return stripped

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Buy groceries and cook dinner",
                "status": "completed"
            }
        }
