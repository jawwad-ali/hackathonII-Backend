"""
Performance Metrics Tracking

Implements timing metrics for key events in the request lifecycle:
- request_received: When a request first arrives
- mcp_tool_called: When an MCP tool is invoked
- gemini_api_called: When Gemini API is called
- request_completed: When a request finishes processing

Features:
- In-memory metrics storage
- Automatic request correlation via request ID
- Thread-safe counters and timers
- Aggregated statistics (count, total time, avg time)

Usage:
    from src.observability.metrics import metrics_tracker

    # Track request start
    metrics_tracker.track_request_received(request_id)

    # Track MCP tool call
    metrics_tracker.track_mcp_tool_called(request_id, tool_name, duration_ms)

    # Track Gemini API call
    metrics_tracker.track_gemini_api_called(request_id, duration_ms)

    # Track request completion
    metrics_tracker.track_request_completed(request_id, duration_ms, success=True)

    # Get metrics summary
    summary = metrics_tracker.get_summary()
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class EventMetrics:
    """
    Metrics for a specific event type.

    Tracks count, total duration, and individual event details.
    """

    count: int = 0
    total_duration_ms: float = 0.0
    events: List[Dict] = field(default_factory=list)

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration in milliseconds."""
        if self.count == 0:
            return 0.0
        return self.total_duration_ms / self.count


@dataclass
class RequestMetrics:
    """
    Metrics for a single request.

    Tracks the lifecycle of a request from received to completed.
    """

    request_id: str
    received_at: float
    completed_at: Optional[float] = None
    success: bool = False
    mcp_calls: int = 0
    gemini_calls: int = 0
    total_duration_ms: Optional[float] = None


class MetricsTracker:
    """
    Thread-safe metrics tracker for application performance monitoring.

    Tracks timing metrics for key events:
    - request_received: Request arrival time
    - mcp_tool_called: MCP tool invocation with duration
    - gemini_api_called: Gemini API call with duration
    - request_completed: Request completion with success status

    Thread-safe for concurrent request processing.
    """

    def __init__(self):
        """Initialize metrics tracker with empty state."""
        self._lock = Lock()

        # Event-level metrics
        self._request_received = EventMetrics()
        self._mcp_tool_called = EventMetrics()
        self._gemini_api_called = EventMetrics()
        self._request_completed = EventMetrics()

        # Request-level metrics (keyed by request_id)
        self._requests: Dict[str, RequestMetrics] = {}

        # Global counters
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0

    def track_request_received(self, request_id: str) -> None:
        """
        Track when a request is received.

        Args:
            request_id: Unique request identifier
        """
        timestamp = time.time()

        with self._lock:
            self._request_received.count += 1
            self._request_received.events.append(
                {"request_id": request_id, "timestamp": timestamp}
            )

            # Initialize request metrics
            self._requests[request_id] = RequestMetrics(
                request_id=request_id, received_at=timestamp
            )

            self._total_requests += 1

    def track_mcp_tool_called(
        self, request_id: str, tool_name: str, duration_ms: float
    ) -> None:
        """
        Track when an MCP tool is called.

        Args:
            request_id: Request identifier for correlation
            tool_name: Name of the MCP tool invoked
            duration_ms: Duration of the tool call in milliseconds
        """
        timestamp = time.time()

        with self._lock:
            self._mcp_tool_called.count += 1
            self._mcp_tool_called.total_duration_ms += duration_ms
            self._mcp_tool_called.events.append(
                {
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "timestamp": timestamp,
                }
            )

            # Update request metrics
            if request_id in self._requests:
                self._requests[request_id].mcp_calls += 1

    def track_gemini_api_called(self, request_id: str, duration_ms: float) -> None:
        """
        Track when Gemini API is called.

        Args:
            request_id: Request identifier for correlation
            duration_ms: Duration of the API call in milliseconds
        """
        timestamp = time.time()

        with self._lock:
            self._gemini_api_called.count += 1
            self._gemini_api_called.total_duration_ms += duration_ms
            self._gemini_api_called.events.append(
                {
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "timestamp": timestamp,
                }
            )

            # Update request metrics
            if request_id in self._requests:
                self._requests[request_id].gemini_calls += 1

    def track_request_completed(
        self, request_id: str, duration_ms: float, success: bool = True
    ) -> None:
        """
        Track when a request is completed.

        Args:
            request_id: Request identifier for correlation
            duration_ms: Total duration of the request in milliseconds
            success: Whether the request completed successfully
        """
        timestamp = time.time()

        with self._lock:
            self._request_completed.count += 1
            self._request_completed.total_duration_ms += duration_ms
            self._request_completed.events.append(
                {
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "success": success,
                    "timestamp": timestamp,
                }
            )

            # Update request metrics
            if request_id in self._requests:
                self._requests[request_id].completed_at = timestamp
                self._requests[request_id].success = success
                self._requests[request_id].total_duration_ms = duration_ms

            # Update global counters
            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

    def get_summary(self) -> Dict:
        """
        Get aggregated metrics summary.

        Returns:
            Dictionary containing:
            - total_requests: Total number of requests received
            - successful_requests: Number of successful requests
            - failed_requests: Number of failed requests
            - request_received: Metrics for request_received events
            - mcp_tool_called: Metrics for MCP tool calls
            - gemini_api_called: Metrics for Gemini API calls
            - request_completed: Metrics for completed requests
        """
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "request_received": {
                    "count": self._request_received.count,
                },
                "mcp_tool_called": {
                    "count": self._mcp_tool_called.count,
                    "total_duration_ms": self._mcp_tool_called.total_duration_ms,
                    "avg_duration_ms": self._mcp_tool_called.avg_duration_ms,
                },
                "gemini_api_called": {
                    "count": self._gemini_api_called.count,
                    "total_duration_ms": self._gemini_api_called.total_duration_ms,
                    "avg_duration_ms": self._gemini_api_called.avg_duration_ms,
                },
                "request_completed": {
                    "count": self._request_completed.count,
                    "total_duration_ms": self._request_completed.total_duration_ms,
                    "avg_duration_ms": self._request_completed.avg_duration_ms,
                },
            }

    def get_request_metrics(self, request_id: str) -> Optional[RequestMetrics]:
        """
        Get metrics for a specific request.

        Args:
            request_id: Request identifier

        Returns:
            RequestMetrics if found, None otherwise
        """
        with self._lock:
            return self._requests.get(request_id)

    def reset(self) -> None:
        """
        Reset all metrics.

        Useful for testing or periodic metrics rotation.
        """
        with self._lock:
            self._request_received = EventMetrics()
            self._mcp_tool_called = EventMetrics()
            self._gemini_api_called = EventMetrics()
            self._request_completed = EventMetrics()
            self._requests.clear()
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0


# Global metrics tracker instance
metrics_tracker = MetricsTracker()
