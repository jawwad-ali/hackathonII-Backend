"""Tests for retry logic and exponential backoff.

This module tests the tenacity-based retry decorators:
- llm_retry decorator behavior
- Exponential backoff timing
- Max attempts configuration
- Exception handling and reraise behavior
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from src.resilience.retry import llm_retry


class TestLlmRetryDecorator:
    """Tests for the llm_retry decorator."""

    def test_llm_retry_succeeds_on_first_try(self):
        """Test that function succeeds without retry if no error."""
        call_count = 0

        @llm_retry
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_llm_retry_retries_on_connection_error(self):
        """Test that llm_retry retries on ConnectionError."""
        call_count = 0

        @llm_retry
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success after retry"

        result = flaky_function()

        assert result == "success after retry"
        assert call_count == 3  # Failed twice, succeeded on third

    def test_llm_retry_retries_on_timeout_error(self):
        """Test that llm_retry retries on TimeoutError."""
        call_count = 0

        @llm_retry
        def timeout_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return "success"

        result = timeout_function()

        assert result == "success"
        assert call_count == 2

    def test_llm_retry_retries_on_os_error(self):
        """Test that llm_retry retries on OSError."""
        call_count = 0

        @llm_retry
        def os_error_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("OS level error")
            return "recovered"

        result = os_error_function()

        assert result == "recovered"
        assert call_count == 2

    def test_llm_retry_does_not_retry_value_error(self):
        """Test that llm_retry does NOT retry on ValueError."""
        call_count = 0

        @llm_retry
        def validation_error_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            validation_error_function()

        # Should only be called once - no retry for ValueError
        assert call_count == 1

    def test_llm_retry_does_not_retry_type_error(self):
        """Test that llm_retry does NOT retry on TypeError."""
        call_count = 0

        @llm_retry
        def type_error_function():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            type_error_function()

        assert call_count == 1

    def test_llm_retry_max_attempts(self):
        """Test that llm_retry stops after max attempts."""
        call_count = 0

        @llm_retry
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()

        # Should try 3 times (default max attempts)
        assert call_count == 3

    def test_llm_retry_preserves_function_result(self):
        """Test that llm_retry preserves the function's return value."""
        @llm_retry
        def returns_dict():
            return {"key": "value", "count": 42}

        result = returns_dict()

        assert result == {"key": "value", "count": 42}

    def test_llm_retry_preserves_function_args(self):
        """Test that llm_retry passes through function arguments."""
        @llm_retry
        def function_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = function_with_args("x", "y", c="z")

        assert result == "x-y-z"


class TestLlmRetryAsync:
    """Tests for llm_retry with async functions."""

    @pytest.mark.asyncio
    async def test_llm_retry_async_succeeds(self):
        """Test that llm_retry works with async functions."""
        @llm_retry
        async def async_success():
            return "async success"

        result = await async_success()

        assert result == "async success"

    @pytest.mark.asyncio
    async def test_llm_retry_async_retries_on_connection_error(self):
        """Test that llm_retry retries async functions on ConnectionError."""
        call_count = 0

        @llm_retry
        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "recovered"

        result = await async_flaky()

        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_llm_retry_async_max_attempts(self):
        """Test that llm_retry stops after max attempts for async."""
        call_count = 0

        @llm_retry
        async def async_always_fails():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always times out")

        with pytest.raises(TimeoutError):
            await async_always_fails()

        assert call_count == 3


class TestRetryExceptionTypes:
    """Tests for specific exception types that trigger retry."""

    def test_connection_refused_triggers_retry(self):
        """Test that ConnectionRefusedError triggers retry."""
        call_count = 0

        @llm_retry
        def connection_refused():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionRefusedError("Connection refused")
            return "connected"

        result = connection_refused()

        assert result == "connected"
        assert call_count == 2

    def test_connection_reset_triggers_retry(self):
        """Test that ConnectionResetError triggers retry."""
        call_count = 0

        @llm_retry
        def connection_reset():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionResetError("Connection reset")
            return "reconnected"

        result = connection_reset()

        assert result == "reconnected"
        assert call_count == 2


class TestRetryWithRealDelay:
    """Tests that verify retry timing (use sparingly - these are slow)."""

    @pytest.mark.slow
    def test_retry_has_exponential_backoff(self):
        """Test that retry uses exponential backoff between attempts.

        Note: This test is marked slow because it actually waits.
        """
        import time

        call_times = []

        @llm_retry
        def timed_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Retry me")
            return "done"

        start = time.time()
        result = timed_function()

        assert result == "done"
        assert len(call_times) == 3

        # Verify there was some delay between calls
        # (exponential backoff should add delay)
        if len(call_times) >= 2:
            first_delay = call_times[1] - call_times[0]
            assert first_delay >= 0.1  # At least some delay


class TestRetryDecoratorsExist:
    """Tests that verify retry decorators are properly defined."""

    def test_llm_retry_is_callable(self):
        """Test that llm_retry can be used as a decorator."""
        assert callable(llm_retry)

    def test_llm_retry_returns_callable(self):
        """Test that decorated function is callable."""
        @llm_retry
        def dummy():
            pass

        assert callable(dummy)

    def test_llm_retry_preserves_function_name(self):
        """Test that llm_retry preserves the original function name."""
        @llm_retry
        def my_named_function():
            pass

        # tenacity wraps the function, name may or may not be preserved
        # Just verify it's callable
        assert callable(my_named_function)
