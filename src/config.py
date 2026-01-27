"""
Configuration Management
Loads and validates environment variables using Pydantic Settings

Includes circuit breaker for OpenAI API calls to prevent cascading failures.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
from datetime import timedelta


# Import resilience components
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
)

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

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key (required)",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4.1-nano",
        description="OpenAI model name (configured via .env)",
    )

    # MCP Server Configuration
    MCP_SERVER_COMMAND: str = Field(default="uvx", description="MCP server command")
    MCP_SERVER_ARGS: str = Field(
        default="fastmcp,run,path/to/todo_server.py",
        description="MCP server arguments (comma-separated)",
    )
    MCP_SERVER_TIMEOUT: int = Field(
        default=60, description="MCP server timeout in seconds"
    )
    MCP_TRANSPORT_TYPE: str = Field(
        default="stdio", description="MCP transport type (stdio or sse)"
    )

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_MCP_FAILURE_THRESHOLD: int = Field(
        default=5, description="MCP circuit breaker failure threshold"
    )
    CIRCUIT_BREAKER_MCP_RECOVERY_TIMEOUT: int = Field(
        default=30, description="MCP circuit breaker recovery timeout in seconds"
    )
    CIRCUIT_BREAKER_LLM_FAILURE_THRESHOLD: int = Field(
        default=3, description="LLM (OpenAI) circuit breaker failure threshold"
    )
    CIRCUIT_BREAKER_LLM_RECOVERY_TIMEOUT: int = Field(
        default=30, description="LLM (OpenAI) circuit breaker recovery timeout in seconds"
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

    # Agent Execution Limits
    AGENT_MAX_TURNS: int = Field(
        default=4, description="Maximum agent turns per request"
    )
    AGENT_MAX_OUTPUT_TOKENS: int = Field(
        default=1024, description="Maximum output tokens per model call"
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

    @field_validator("MCP_TRANSPORT_TYPE")
    @classmethod
    def validate_mcp_transport_type(cls, v: str) -> str:
        """
        Validate MCP transport type is either 'stdio' or 'sse'.

        Args:
            v: Transport type string

        Returns:
            Lowercase transport type string

        Raises:
            ValueError: If transport type is invalid
        """
        valid_types = ["stdio", "sse"]
        v_lower = v.lower()
        if v_lower not in valid_types:
            raise ValueError(f"MCP_TRANSPORT_TYPE must be one of {valid_types}")
        return v_lower

    class Config:
        """Pydantic configuration"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()

# Global circuit breaker for OpenAI API
# Configuration:
# - 3 consecutive failures before opening
# - 30 second recovery timeout
# - 2 test calls in half-open state
_llm_circuit_breaker = CircuitBreaker(
    name="openai_api",
    config=CircuitBreakerConfig(
        failure_threshold=settings.CIRCUIT_BREAKER_LLM_FAILURE_THRESHOLD,
        recovery_timeout=timedelta(seconds=settings.CIRCUIT_BREAKER_LLM_RECOVERY_TIMEOUT),
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


def get_openai_model() -> str:
    """
    Get the configured OpenAI model name from OPENAI_MODEL env var.

    Returns:
        str: OpenAI model name as configured in .env
    """
    return settings.OPENAI_MODEL


def get_llm_circuit_breaker() -> CircuitBreaker:
    """
    Get the LLM (OpenAI) API circuit breaker for monitoring.

    This function provides access to the circuit breaker instance for:
    - Health check endpoints
    - Monitoring dashboards
    - Manual circuit breaker reset (administrative use)

    Returns:
        CircuitBreaker: The global OpenAI API circuit breaker

    Example:
        >>> breaker = get_llm_circuit_breaker()
        >>> state = breaker.get_state()
        >>> print(f"Circuit state: {state.state.value}")
        >>> print(f"Failure count: {state.failure_count}")
    """
    return _llm_circuit_breaker
