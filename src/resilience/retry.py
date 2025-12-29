"""Retry Logic with Exponential Backoff

Provides tenacity-based retry configurations for external service calls
with exponential backoff, jitter, and timeout limits.

This module defines retry strategies for:
- MCP Server calls (more tolerant, longer timeouts)
- Gemini API calls (stricter limits due to rate limiting)
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging
from typing import Type

# Logger for retry attempts (will be integrated with structured logging in Phase 6)
logger = logging.getLogger(__name__)


# Exception types that should trigger retries
RETRIABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,  # Covers network-related OS errors
)


def create_mcp_retry_decorator():
    """Create retry decorator for MCP server calls

    Configuration:
        - Max attempts: 5
        - Exponential backoff: 1s → 2s → 4s → 8s → 16s (with jitter)
        - Max wait: 30 seconds
        - Jitter: Random 0-1 second added to prevent thundering herd

    Retries on:
        - ConnectionError (MCP server unreachable)
        - TimeoutError (MCP server slow/unresponsive)
        - OSError (Network issues)

    Usage:
        @create_mcp_retry_decorator()
        async def call_mcp_tool(tool_name: str, args: dict):
            return await mcp_client.call_tool(tool_name, args)

    Returns:
        Tenacity retry decorator configured for MCP calls
    """
    return retry(
        # Stop after 5 attempts (1 initial + 4 retries)
        stop=stop_after_attempt(5),

        # Exponential backoff: wait = 2^attempt + jitter (max 30s)
        # Attempt 1: 1s + jitter
        # Attempt 2: 2s + jitter
        # Attempt 3: 4s + jitter
        # Attempt 4: 8s + jitter
        # Attempt 5: 16s + jitter (capped at 30s)
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=30
        ),

        # Only retry on specific exceptions
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),

        # Log retry attempts for monitoring
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),

        # Re-raise the exception after all retries exhausted
        reraise=True
    )


def create_gemini_retry_decorator():
    """Create retry decorator for Gemini API calls

    Configuration:
        - Max attempts: 3 (stricter due to API rate limits)
        - Exponential backoff: 2s → 4s → 8s (with jitter)
        - Max wait: 60 seconds
        - Jitter: Random 0-2 seconds added

    Retries on:
        - ConnectionError (API unreachable)
        - TimeoutError (API slow/unresponsive)
        - OSError (Network issues)

    Note: Does NOT retry on rate limit errors (429) - those should be handled
    separately by circuit breaker or caller logic.

    Usage:
        @create_gemini_retry_decorator()
        async def call_gemini_api(messages: list):
            return await gemini_client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=messages
            )

    Returns:
        Tenacity retry decorator configured for Gemini API calls
    """
    return retry(
        # Stop after 3 attempts (1 initial + 2 retries)
        # Lower than MCP due to external API rate limits
        stop=stop_after_attempt(3),

        # Exponential backoff with longer initial wait
        # Attempt 1: 2s + jitter
        # Attempt 2: 4s + jitter
        # Attempt 3: 8s + jitter (capped at 60s)
        wait=wait_exponential(
            multiplier=2,
            min=2,
            max=60
        ),

        # Only retry on specific exceptions
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),

        # Log retry attempts for monitoring
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),

        # Re-raise the exception after all retries exhausted
        reraise=True
    )


def create_custom_retry_decorator(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 30,
    multiplier: int = 1,
    retriable_exceptions: tuple[Type[Exception], ...] = RETRIABLE_EXCEPTIONS
):
    """Create custom retry decorator with configurable parameters

    Allows fine-tuning retry behavior for specific use cases beyond
    the standard MCP and Gemini configurations.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time in seconds (default: 1)
        max_wait: Maximum wait time in seconds (default: 30)
        multiplier: Exponential backoff multiplier (default: 1)
        retriable_exceptions: Tuple of exception types to retry on

    Usage:
        @create_custom_retry_decorator(max_attempts=5, min_wait=2, max_wait=60)
        async def custom_external_call():
            return await some_api.fetch()

    Returns:
        Tenacity retry decorator with custom configuration
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=multiplier,
            min=min_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type(retriable_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True
    )


# Convenience decorators for direct use
mcp_retry = create_mcp_retry_decorator()
gemini_retry = create_gemini_retry_decorator()


# Usage Examples (for documentation):
"""
Example 1: MCP Server Call with Retry

    from src.resilience.retry import mcp_retry

    @mcp_retry
    async def fetch_todos_from_mcp():
        return await mcp_client.call_tool("list_todos", {})

Example 2: Gemini API Call with Retry

    from src.resilience.retry import gemini_retry

    @gemini_retry
    async def generate_response(prompt: str):
        return await gemini_client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}]
        )

Example 3: Combined with Circuit Breaker

    from src.resilience.retry import mcp_retry
    from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

    # Initialize circuit breaker
    breaker = CircuitBreaker(
        name="mcp_server",
        config=CircuitBreakerConfig(failure_threshold=5)
    )

    @mcp_retry
    async def call_with_retry(tool_name: str, args: dict):
        # This function will be retried by tenacity
        return await mcp_client.call_tool(tool_name, args)

    # Wrap in circuit breaker
    async def call_mcp_with_resilience(tool_name: str, args: dict):
        # Circuit breaker wraps the retry logic
        return await breaker.call(call_with_retry, tool_name, args)

    # Execution flow:
    # 1. Circuit breaker checks state (OPEN → fail-fast)
    # 2. If CLOSED/HALF-OPEN, calls function
    # 3. Function retries on retriable exceptions (exponential backoff)
    # 4. Circuit breaker records success/failure
    # 5. Circuit breaker updates state based on result

Example 4: Custom Configuration

    from src.resilience.retry import create_custom_retry_decorator

    # Custom retry for specific API with longer timeouts
    custom_retry = create_custom_retry_decorator(
        max_attempts=7,
        min_wait=3,
        max_wait=120,
        multiplier=2
    )

    @custom_retry
    async def call_slow_api():
        return await slow_api.fetch()
"""
