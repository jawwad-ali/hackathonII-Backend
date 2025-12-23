"""
Request and response schemas for the AI Agent Orchestrator API.

This module defines Pydantic models for input validation and sanitization
per FR-013 requirements.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """
    Schema for incoming chat requests to the streaming endpoint.

    Implements FR-013 requirements:
    - Maximum 5000 character input limit
    - UTF-8 encoding validation
    - Control character stripping
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's natural language input for todo operations"
    )

    request_id: Optional[str] = Field(
        None,
        description="Optional client-provided request ID for correlation"
    )

    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """
        Sanitize user input by:
        1. Validating UTF-8 encoding (Pydantic handles this automatically)
        2. Stripping control characters (except newlines and tabs)
        3. Normalizing whitespace

        Args:
            v: Raw message string

        Returns:
            Sanitized message string

        Raises:
            ValueError: If message is empty after sanitization
        """
        # Strip control characters (keep newline \n and tab \t)
        # Control characters are in ranges: \x00-\x08, \x0B-\x0C, \x0E-\x1F, \x7F-\x9F
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', v)

        # Normalize whitespace (replace multiple spaces with single space)
        sanitized = ' '.join(sanitized.split())

        # Validate not empty after sanitization
        if not sanitized.strip():
            raise ValueError("Message is empty after sanitization")

        return sanitized

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "message": "Remind me to buy eggs tomorrow at 3pm",
                "request_id": "req_123abc"
            }
        }


class HealthResponse(BaseModel):
    """
    Schema for /health endpoint response.

    Includes circuit breaker states and metrics per openapi.yaml requirements.
    """

    status: str = Field(
        ...,
        description="Overall health status: 'healthy', 'degraded', or 'unhealthy'"
    )

    circuit_breakers: dict = Field(
        default_factory=dict,
        description="Circuit breaker states for external dependencies"
    )

    uptime_seconds: Optional[float] = Field(
        None,
        description="Service uptime in seconds since last restart"
    )

    metrics: Optional[dict] = Field(
        None,
        description="Performance metrics (request counts, success rates, etc.)"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "circuit_breakers": {
                    "mcp_server": "closed",
                    "gemini_api": "closed"
                },
                "uptime_seconds": 3600.5,
                "metrics": {
                    "total_requests": 150,
                    "successful_requests": 148,
                    "failed_requests": 2
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Schema for error responses.

    Ensures user-friendly error messages without exposing internal details.
    """

    error: str = Field(
        ...,
        description="User-friendly error message"
    )

    error_code: Optional[str] = Field(
        None,
        description="Machine-readable error code for client handling"
    )

    request_id: Optional[str] = Field(
        None,
        description="Request ID for correlation and debugging"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "error": "The todo service is temporarily unavailable. Please try again in a few moments.",
                "error_code": "SERVICE_UNAVAILABLE",
                "request_id": "req_123abc"
            }
        }
