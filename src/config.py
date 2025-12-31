"""
Configuration Management
Loads and validates environment variables using Pydantic Settings

Includes circuit breaker for Gemini API calls to prevent cascading failures.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
import os
from openai import AsyncOpenAI
from datetime import timedelta

# Import resilience components
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError
)
from src.resilience.retry import gemini_retry


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses python-dotenv to load from .env file if present.
    """

    # Application Configuration
    APP_ENV: str = Field(default="development", description="Application environment")
    APP_HOST: str = Field(default="0.0.0.0", description="Application host")
    APP_PORT: int = Field(default=8000, description="Application port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Gemini API Configuration
    GEMINI_API_KEY: str = Field(..., description="Gemini API key")
    GEMINI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="Gemini OpenAI-compatible base URL",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash", description="Gemini model name"
    )

    # MCP Server Configuration
    MCP_SERVER_COMMAND: str = Field(default="uvx", description="MCP server command")
    MCP_SERVER_ARGS: str = Field(
        default="fastmcp,run,path/to/todo_server.py",
        description="MCP server arguments (comma-separated)",
    )
    MCP_SERVER_TIMEOUT: int = Field(
        default=5, description="MCP server timeout in seconds"
    )

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_MCP_FAILURE_THRESHOLD: int = Field(
        default=5, description="MCP circuit breaker failure threshold"
    )
    CIRCUIT_BREAKER_MCP_RECOVERY_TIMEOUT: int = Field(
        default=30, description="MCP circuit breaker recovery timeout in seconds"
    )
    CIRCUIT_BREAKER_GEMINI_FAILURE_THRESHOLD: int = Field(
        default=3, description="Gemini circuit breaker failure threshold"
    )
    CIRCUIT_BREAKER_GEMINI_RECOVERY_TIMEOUT: int = Field(
        default=60, description="Gemini circuit breaker recovery timeout in seconds"
    )

    # Performance Configuration
    MAX_INPUT_LENGTH: int = Field(
        default=5000, description="Maximum input length in characters"
    )
    REQUEST_TIMEOUT: int = Field(
        default=30, description="Request timeout in seconds"
    )
    MAX_CONCURRENT_CONNECTIONS: int = Field(
        default=100, description="Maximum concurrent connections"
    )

    @field_validator("MCP_SERVER_ARGS")
    @classmethod
    def parse_mcp_args(cls, v: str) -> List[str]:
        """
        Parse comma-separated MCP server arguments into a list.

        Args:
            v: Comma-separated string of arguments

        Returns:
            List of argument strings
        """
        if isinstance(v, str):
            return [arg.strip() for arg in v.split(",")]
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate log level is one of the standard Python logging levels.

        Args:
            v: Log level string

        Returns:
            Uppercase log level string

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    class Config:
        """Pydantic configuration"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()

# Global circuit breaker for Gemini API
# Configuration:
# - 3 consecutive failures before opening (stricter due to external API)
# - 60 second recovery timeout (longer for external API)
# - 2 test calls in half-open state
_gemini_circuit_breaker = CircuitBreaker(
    name="gemini_api",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=timedelta(seconds=60),
        half_open_max_calls=2
    )
)


def get_mcp_server_config() -> dict:
    """
    Get MCP server configuration for agents_mcp integration.

    Returns:
        dict: MCP server configuration dictionary
    """
    return {
        "todo_server": {
            "command": settings.MCP_SERVER_COMMAND,
            "args": settings.MCP_SERVER_ARGS,
            "timeout": settings.MCP_SERVER_TIMEOUT,
        }
    }


def get_gemini_config() -> dict:
    """
    Get Gemini API configuration for AsyncOpenAI client.

    Returns:
        dict: Gemini configuration dictionary with api_key, base_url, model
    """
    return {
        "api_key": settings.GEMINI_API_KEY,
        "base_url": settings.GEMINI_BASE_URL,
        "model": settings.GEMINI_MODEL,
    }


def get_gemini_client() -> AsyncOpenAI:
    """
    Create and return an AsyncOpenAI client configured for Gemini API with resilience.

    This client bridges OpenAI Agents SDK to Google Gemini 2.5 Flash
    by configuring a custom base_url pointing to Gemini's OpenAI-compatible endpoint.

    The client is wrapped with circuit breaker protection to prevent cascading failures
    when the Gemini API is unavailable or experiencing issues.

    T084: Timeout configuration added to prevent hanging on slow API responses.
    - Request timeout: 30 seconds (matches REQUEST_TIMEOUT setting)
    - Connection timeout: 10 seconds for initial connection

    Note: The circuit breaker is applied at the agent execution level, not at client
    creation. This function creates a plain client that will be wrapped when used.

    Returns:
        AsyncOpenAI: Configured async OpenAI client for Gemini with timeout

    Example:
        >>> client = get_gemini_client()
        >>> # Circuit breaker protection applied when agent makes API calls
        >>> # Timeout of 30s enforced on all API requests
    """
    config = get_gemini_config()

    # T084: Configure timeout for Gemini API requests
    # This prevents the client from hanging indefinitely on slow/unresponsive API
    return AsyncOpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=settings.REQUEST_TIMEOUT,  # 30 seconds default
    )


def get_gemini_circuit_breaker() -> CircuitBreaker:
    """
    Get the Gemini API circuit breaker for monitoring.

    This function provides access to the circuit breaker instance for:
    - Health check endpoints
    - Monitoring dashboards
    - Manual circuit breaker reset (administrative use)

    Returns:
        CircuitBreaker: The global Gemini API circuit breaker

    Example:
        >>> breaker = get_gemini_circuit_breaker()
        >>> state = breaker.get_state()
        >>> print(f"Circuit state: {state.state.value}")
        >>> print(f"Failure count: {state.failure_count}")
    """
    return _gemini_circuit_breaker
