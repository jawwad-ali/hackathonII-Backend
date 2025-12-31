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

    thread_id: Optional[str] = Field(
        None,
        description="Optional thread ID for conversation tracking across multiple requests"
    )

    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """
        Sanitize user input per FR-013 requirements (T087):
        1. Validating UTF-8 encoding (Pydantic handles this automatically)
        2. Stripping control characters (except newline, tab, carriage return)
        3. Normalizing whitespace

        T087: Control character stripping implementation:
        - Keep: \\n (newline, 0x0A), \\t (tab, 0x09), \\r (carriage return, 0x0D)
        - Remove: All other control characters in ranges 0x00-0x1F and 0x7F-0x9F

        Args:
            v: Raw message string

        Returns:
            Sanitized message string

        Raises:
            ValueError: If message is empty after sanitization
        """
        # T087: Strip control characters per FR-013
        # Keep: \n (0x0A), \t (0x09), \r (0x0D)
        # Remove ranges: 0x00-0x08 (before tab), 0x0B-0x0C (between newline and carriage return),
        #                0x0E-0x1F (after carriage return), 0x7F-0x9F (extended control chars)
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', v)

        # Normalize whitespace (replace multiple spaces with single space)
        # This also handles tabs and newlines in the normalization
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
                "request_id": "req_123abc",
                "thread_id": "thread_456def"
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

    T019: Added status field to distinguish between error types:
    - "error": General error condition
    - "degraded": Service operating in degraded mode (partial functionality available)
    """

    error: str = Field(
        ...,
        description="User-friendly error message"
    )

    status: Optional[str] = Field(
        default="error",
        description="Error status type: 'error' (general failure) or 'degraded' (partial functionality)"
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
                "status": "degraded",
                "error_code": "SERVICE_UNAVAILABLE",
                "request_id": "req_123abc"
            }
        }
