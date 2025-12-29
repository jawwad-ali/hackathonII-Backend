"""Pydantic validation schemas for MCP tool inputs.

This module defines input validation schemas for all MCP tools.
These schemas provide type safety, validation, and clear error messages
for tool callers.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .models import TodoStatus


class CreateTodoInput(BaseModel):
    """Input schema for create_todo tool.

    Validates todo creation requests with field-level constraints
    and custom validation logic.

    Attributes:
        title: Todo title (required, 1-200 chars after stripping whitespace)
        description: Optional description (max 2000 chars)
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

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "title": "Buy groceries",
                "description": "Milk, eggs, bread, and coffee"
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
