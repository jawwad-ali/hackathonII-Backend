"""Circuit Breaker Pattern Implementation

Implements a circuit breaker pattern for external service dependencies
to prevent cascading failures and enable graceful degradation.

State Machine:
    CLOSED (normal) → OPEN (fail-fast) → HALF-OPEN (test) → CLOSED

- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, fail fast without calling service
- HALF-OPEN: Testing if service recovered, limited requests allowed
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"           # Normal operation
    OPEN = "open"               # Failing fast
    HALF_OPEN = "half_open"     # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery (OPEN → HALF-OPEN)
        half_open_max_calls: Maximum test calls allowed in HALF-OPEN state

    Examples:
        # MCP Server configuration (more tolerant)
        mcp_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=timedelta(seconds=30),
            half_open_max_calls=3
        )

        # Gemini API configuration (less tolerant due to rate limits)
        gemini_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=timedelta(seconds=60),
            half_open_max_calls=2
        )
    """
    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=30)
    half_open_max_calls: int = 3

    def __post_init__(self):
        """Validate configuration values"""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout.total_seconds() < 0:
            raise ValueError("recovery_timeout must be positive")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")


@dataclass
class CircuitBreakerState:
    """Current state of a circuit breaker

    Tracks the circuit breaker's current state and metrics for
    state transition decisions.

    Attributes:
        state: Current circuit state (closed/open/half_open)
        failure_count: Consecutive failures in current state
        last_failure_time: Timestamp of most recent failure
        last_state_change: Timestamp of last state transition
        consecutive_successes: Success count in HALF-OPEN state

    State Transitions:
        CLOSED → OPEN: When failure_count >= config.failure_threshold
        OPEN → HALF-OPEN: When time since last_failure_time >= config.recovery_timeout
        HALF-OPEN → CLOSED: When consecutive_successes >= config.half_open_max_calls
        HALF-OPEN → OPEN: When any failure occurs in HALF-OPEN state
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: datetime | None = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    consecutive_successes: int = 0

    def to_dict(self) -> dict:
        """Convert state to dictionary for logging/monitoring

        Returns:
            Dict with state information suitable for JSON serialization

        Example:
            {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": "2025-12-25T12:00:00Z",
                "last_state_change": "2025-12-25T11:00:00Z",
                "consecutive_successes": 0
            }
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat(),
            "consecutive_successes": self.consecutive_successes
        }


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and prevents operation"""

    def __init__(self, service_name: str, state: CircuitBreakerState):
        self.service_name = service_name
        self.state = state
        super().__init__(
            f"Circuit breaker for '{service_name}' is {state.state.value}. "
            f"Service temporarily unavailable."
        )


class CircuitBreaker:
    """Circuit Breaker implementation with state machine logic

    Manages state transitions for a single service dependency to prevent
    cascading failures and enable graceful degradation.

    Usage:
        # Initialize circuit breaker
        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=timedelta(seconds=30))
        breaker = CircuitBreaker(name="mcp_server", config=config)

        # Before calling external service
        try:
            await breaker.call(async_function, *args, **kwargs)
        except CircuitBreakerError as e:
            # Handle circuit open - service unavailable
            logger.warning(f"Circuit breaker open: {e}")
            # Return fallback response
        except Exception as e:
            # Handle actual service error
            logger.error(f"Service error: {e}")

    State Transitions:
        CLOSED → OPEN: When failure_count >= config.failure_threshold
        OPEN → HALF-OPEN: When time since last_failure_time >= config.recovery_timeout
        HALF-OPEN → CLOSED: When consecutive_successes >= config.half_open_max_calls
        HALF-OPEN → OPEN: When any failure occurs in HALF-OPEN state
    """

    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker

        Args:
            name: Service name for logging and error messages
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitBreakerState()

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should transition from OPEN to HALF-OPEN

        Returns:
            True if recovery timeout has elapsed since last failure
        """
        if self.state.state != CircuitState.OPEN:
            return False

        if self.state.last_failure_time is None:
            return False

        elapsed = datetime.utcnow() - self.state.last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _transition_to_half_open(self) -> None:
        """Transition circuit from OPEN to HALF-OPEN state"""
        old_state = self.state.state
        self.state.state = CircuitState.HALF_OPEN
        self.state.consecutive_successes = 0
        self.state.last_state_change = datetime.utcnow()

        # Log state transition for monitoring
        self._log_state_change(old_state, CircuitState.HALF_OPEN)

    def _transition_to_open(self, error: Exception | None = None) -> None:
        """Transition circuit to OPEN state

        Args:
            error: Optional exception that triggered the transition
        """
        old_state = self.state.state
        self.state.state = CircuitState.OPEN
        self.state.last_failure_time = datetime.utcnow()
        self.state.last_state_change = datetime.utcnow()
        self.state.consecutive_successes = 0

        # Log state transition for monitoring
        self._log_state_change(old_state, CircuitState.OPEN, error)

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state (normal operation)"""
        old_state = self.state.state
        self.state.state = CircuitState.CLOSED
        self.state.failure_count = 0
        self.state.consecutive_successes = 0
        self.state.last_state_change = datetime.utcnow()

        # Log state transition for monitoring
        self._log_state_change(old_state, CircuitState.CLOSED)

    def _log_state_change(
        self,
        old_state: CircuitState,
        new_state: CircuitState,
        error: Exception | None = None
    ) -> None:
        """Log circuit breaker state change for monitoring

        Args:
            old_state: Previous circuit state
            new_state: New circuit state
            error: Optional error that triggered the change
        """
        # TODO: Integrate with structured logging in Phase 6
        # For now, this is a placeholder for future logging integration
        log_data = {
            "event": "circuit_breaker_state_change",
            "service": self.name,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "failure_count": self.state.failure_count,
            "last_error": str(error) if error else None
        }
        # Will be replaced with proper structured logger
        print(f"[CircuitBreaker] {log_data}")

    def _record_success(self) -> None:
        """Record successful operation and update state accordingly"""
        if self.state.state == CircuitState.HALF_OPEN:
            self.state.consecutive_successes += 1

            # Transition to CLOSED if enough successes in HALF-OPEN
            if self.state.consecutive_successes >= self.config.half_open_max_calls:
                self._transition_to_closed()

        elif self.state.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.state.failure_count = 0

    def _record_failure(self, error: Exception) -> None:
        """Record failed operation and update state accordingly

        Args:
            error: Exception that caused the failure
        """
        self.state.last_failure_time = datetime.utcnow()

        if self.state.state == CircuitState.HALF_OPEN:
            # Any failure in HALF-OPEN immediately opens circuit
            self._transition_to_open(error)

        elif self.state.state == CircuitState.CLOSED:
            self.state.failure_count += 1

            # Transition to OPEN if threshold exceeded
            if self.state.failure_count >= self.config.failure_threshold:
                self._transition_to_open(error)

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by func (after recording failure)

        Example:
            async def fetch_data():
                return await external_api.get("/data")

            try:
                result = await breaker.call(fetch_data)
            except CircuitBreakerError:
                # Circuit is open, use fallback
                result = get_cached_data()
        """
        # Check if we should attempt reset from OPEN to HALF-OPEN
        if self._should_attempt_reset():
            self._transition_to_half_open()

        # If circuit is OPEN, fail fast
        if self.state.state == CircuitState.OPEN:
            raise CircuitBreakerError(self.name, self.state)

        # Attempt the operation
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise  # Re-raise the original exception

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state

        Returns:
            Current state (for monitoring/health checks)
        """
        return self.state

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state

        Warning: Use with caution. Manual resets bypass the state machine
        and should only be used for administrative purposes.
        """
        self._transition_to_closed()
