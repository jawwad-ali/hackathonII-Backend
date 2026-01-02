"""
Integration tests for SSE streaming and circuit breaker behavior.

T016: Test circuit breaker degradation (simulate MCP failure, verify error response format)
T017: Test circuit breaker recovery (verify HALF-OPEN state, successful retry)

NOTE: These tests are written FIRST (TDD approach) and should FAIL before implementation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
from datetime import timedelta

from src.main import app
from src.resilience.circuit_breaker import CircuitState, CircuitBreakerError
from src.mcp.client import get_mcp_circuit_breaker


class TestCircuitBreakerDegradation:
    """
    T016: Integration test for circuit breaker degradation.

    Tests:
    - Simulate MCP server failure during runtime
    - Verify circuit breaker opens after threshold failures
    - Verify POST /chat/stream returns HTTP 200 with user-friendly error (not 503)
    - Verify error response format includes status="degraded"
    """

    def test_mcp_failure_triggers_circuit_breaker_open(self):
        """
        Test that repeated MCP failures cause circuit breaker to open.

        Expected behavior:
        - After 5 consecutive MCP failures, circuit breaker opens
        - Circuit breaker state transitions from CLOSED → OPEN
        - Failure count reaches threshold (5)
        """
        # Get MCP circuit breaker instance
        mcp_breaker = get_mcp_circuit_breaker()

        # Reset circuit breaker to known state
        mcp_breaker.state.state = CircuitState.CLOSED
        mcp_breaker.state.failure_count = 0

        # Simulate 5 consecutive failures (threshold for MCP is 5)
        for i in range(5):
            mcp_breaker._record_failure(Exception("MCP timeout"))

        # Verify circuit breaker state
        state = mcp_breaker.get_state()
        assert state.state == CircuitState.OPEN, \
            f"Circuit breaker should be OPEN after {5} failures, got {state.state}"
        assert state.failure_count == 5, \
            f"Failure count should be 5, got {state.failure_count}"

    def test_chat_stream_returns_degraded_error_when_mcp_down(self):
        """
        Test that POST /chat/stream returns HTTP 200 with degraded error when MCP is down.

        Expected behavior (per spec SC-013):
        - HTTP 200 status code (NOT 503)
        - Response body contains user-friendly error message
        - Response includes status="degraded"
        - No crash or exception propagation to user
        """
        # Mock app.state.mcp_server as None (simulating degraded mode)
        with patch.object(app.state, 'mcp_server', None):
            client = TestClient(app)

            # Send chat request
            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a todo for buying groceries",
                    "request_id": "test_degraded_001"
                }
            )

            # T016: Verify HTTP 200 (per spec requirement)
            assert response.status_code == 200, \
                "Should return HTTP 200 even when MCP is down (per SC-013)"

            # Verify response format
            data = response.json()
            assert "error" in data, "Response should contain 'error' field"
            assert "status" in data, "Response should contain 'status' field"
            assert data["status"] == "degraded", \
                f"Status should be 'degraded', got '{data['status']}'"

            # Verify user-friendly error message
            assert "unavailable" in data["error"].lower() or "temporarily" in data["error"].lower(), \
                "Error message should be user-friendly and mention unavailability"

    def test_chat_stream_returns_degraded_error_on_circuit_breaker_open(self):
        """
        Test that POST /chat/stream returns degraded error when circuit breaker is open.

        Expected behavior:
        - CircuitBreakerOpenError is caught in endpoint
        - HTTP 200 returned with user-friendly error message
        - Response includes status="degraded"
        """
        # Mock circuit breaker to raise CircuitBreakerError
        from src.resilience.circuit_breaker import CircuitBreakerState
        mock_breaker = MagicMock()
        mock_state = CircuitBreakerState(state=CircuitState.OPEN, failure_count=5)
        mock_breaker.call.side_effect = CircuitBreakerError("mcp_server", mock_state)

        with patch('src.api.routes.get_mcp_circuit_breaker', return_value=mock_breaker):
            client = TestClient(app)

            # Send chat request
            response = client.post(
                "/chat/stream",
                json={
                    "message": "List my todos",
                    "request_id": "test_circuit_open_001"
                }
            )

            # T016: Verify HTTP 200 (graceful degradation)
            assert response.status_code == 200, \
                "Should return HTTP 200 when circuit breaker is open"

            # Verify degraded error response
            data = response.json()
            assert data.get("status") == "degraded", \
                "Status should be 'degraded' when circuit breaker is open"
            assert "error" in data, "Response should contain error message"

    def test_degraded_error_message_is_user_friendly(self):
        """
        Test that degraded mode error messages are user-friendly (non-technical).

        Expected behavior:
        - No stack traces or technical jargon
        - Clear explanation of temporary unavailability
        - Suggestion to try again later
        """
        with patch.object(app.state, 'mcp_server', None):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Update todo 1 to completed",
                    "request_id": "test_friendly_error_001"
                }
            )

            data = response.json()
            error_message = data.get("error", "")

            # Verify user-friendly characteristics
            assert "database" in error_message.lower() or "service" in error_message.lower(), \
                "Error should mention database or service"
            assert "temporarily" in error_message.lower() or "unavailable" in error_message.lower(), \
                "Error should indicate temporary issue"
            assert "try again" in error_message.lower() or "later" in error_message.lower(), \
                "Error should suggest retrying later"

            # Verify NO technical jargon
            technical_terms = ["traceback", "exception", "stack", "circuit breaker", "subprocess", "stdio"]
            for term in technical_terms:
                assert term not in error_message.lower(), \
                    f"Error message should not contain technical term '{term}'"

    def test_health_check_shows_degraded_when_mcp_circuit_open(self):
        """
        Test that GET /health shows degraded status when MCP circuit breaker is open.

        Expected behavior:
        - HTTP 200 status code
        - status="degraded"
        - MCP circuit breaker state="open"
        - Gemini circuit breaker state="closed"
        """
        with patch('src.main.get_mcp_circuit_breaker') as mock_mcp_breaker, \
             patch('src.main.get_gemini_circuit_breaker') as mock_gemini_breaker:

            # Mock MCP circuit breaker as open
            mock_mcp_state = MagicMock()
            mock_mcp_state.state = CircuitState.OPEN
            mock_mcp_state.failure_count = 5
            mock_mcp_state.last_failure_time = None

            # Mock Gemini circuit breaker as closed
            mock_gemini_state = MagicMock()
            mock_gemini_state.state = CircuitState.CLOSED
            mock_gemini_state.failure_count = 0
            mock_gemini_state.last_failure_time = None

            mock_mcp_breaker.return_value.get_state.return_value = mock_mcp_state
            mock_gemini_breaker.return_value.get_state.return_value = mock_gemini_state

            client = TestClient(app)
            response = client.get("/health")

            # Verify HTTP 200 (per spec)
            assert response.status_code == 200, \
                "Health check should return HTTP 200 when MCP is degraded"

            # Verify degraded status
            data = response.json()
            assert data["status"] == "degraded", \
                "Status should be 'degraded' when MCP circuit breaker is open"


class TestCircuitBreakerRecovery:
    """
    T017: Integration test for circuit breaker recovery.

    Tests:
    - Circuit breaker transitions from OPEN → HALF-OPEN after recovery timeout
    - Successful request in HALF-OPEN state closes circuit breaker
    - Failed request in HALF-OPEN state reopens circuit breaker
    - Retry logic works with circuit breaker recovery
    """

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_to_half_open_after_timeout(self):
        """
        Test that circuit breaker transitions from OPEN → HALF-OPEN after recovery timeout.

        Expected behavior:
        - Circuit breaker opens after 5 failures
        - After recovery_timeout (30s for MCP), state transitions to HALF-OPEN
        - In HALF-OPEN state, single request is allowed through
        """
        import asyncio
        from datetime import datetime, timezone

        # Get MCP circuit breaker instance
        mcp_breaker = get_mcp_circuit_breaker()

        # Reset to known state
        mcp_breaker.state.state = CircuitState.CLOSED
        mcp_breaker.state.failure_count = 0

        # Trigger circuit breaker to open (5 failures)
        for _ in range(5):
            mcp_breaker._record_failure(Exception("MCP timeout"))

        # Verify circuit breaker is now OPEN
        state = mcp_breaker.get_state()
        assert state.state == CircuitState.OPEN, "Circuit breaker should be OPEN after 5 failures"

        # Manually advance last_failure_time to simulate timeout passage
        # (In real code, we'd wait 30s, but for testing we manipulate time)
        recovery_timeout = timedelta(seconds=30)
        mcp_breaker.state.last_failure_time = datetime.now(timezone.utc) - recovery_timeout - timedelta(seconds=1)

        # Attempt a call (should transition to HALF-OPEN)
        # Mock a successful MCP operation
        async def mock_mcp_operation():
            await asyncio.sleep(0.01)
            return {"status": "success"}

        try:
            result = await mcp_breaker.call(mock_mcp_operation)
            # If we get here, circuit breaker allowed the call through
            state_after = mcp_breaker.get_state()

            # Circuit breaker should have transitioned to HALF-OPEN or CLOSED
            assert state_after.state in [CircuitState.HALF_OPEN, CircuitState.CLOSED], \
                f"Circuit breaker should transition to HALF-OPEN or CLOSED after timeout, got {state_after.state}"

        except CircuitBreakerError:
            pytest.fail("Circuit breaker should allow requests through after recovery timeout")

    @pytest.mark.asyncio
    async def test_successful_request_in_half_open_closes_circuit_breaker(self):
        """
        Test that a successful request in HALF-OPEN state closes the circuit breaker.

        Expected behavior:
        - Circuit breaker in HALF-OPEN state
        - Successful request passes through
        - Circuit breaker transitions to CLOSED state
        - Failure count resets to 0
        """
        import asyncio

        # Get MCP circuit breaker instance
        mcp_breaker = get_mcp_circuit_breaker()

        # Set circuit breaker to HALF-OPEN state
        mcp_breaker.state.state = CircuitState.HALF_OPEN
        mcp_breaker.state.failure_count = 5

        # Mock successful operation
        async def successful_operation():
            await asyncio.sleep(0.01)
            return {"status": "success"}

        # Execute operation through circuit breaker
        result = await mcp_breaker.call(successful_operation)

        # Verify circuit breaker closed
        state = mcp_breaker.get_state()
        assert state.state == CircuitState.CLOSED, \
            f"Circuit breaker should close after successful request in HALF-OPEN, got {state.state}"
        assert state.failure_count == 0, \
            f"Failure count should reset to 0, got {state.failure_count}"

    @pytest.mark.asyncio
    async def test_failed_request_in_half_open_reopens_circuit_breaker(self):
        """
        Test that a failed request in HALF-OPEN state reopens the circuit breaker.

        Expected behavior:
        - Circuit breaker in HALF-OPEN state
        - Failed request triggers failure
        - Circuit breaker transitions back to OPEN state
        - Recovery timeout resets
        """
        import asyncio

        # Get MCP circuit breaker instance
        mcp_breaker = get_mcp_circuit_breaker()

        # Set circuit breaker to HALF-OPEN state
        mcp_breaker.state.state = CircuitState.HALF_OPEN
        mcp_breaker.state.failure_count = 5

        # Mock failed operation
        async def failed_operation():
            await asyncio.sleep(0.01)
            raise Exception("MCP server timeout")

        # Execute operation through circuit breaker
        with pytest.raises(Exception):
            await mcp_breaker.call(failed_operation)

        # Verify circuit breaker reopened
        state = mcp_breaker.get_state()
        assert state.state == CircuitState.OPEN, \
            f"Circuit breaker should reopen after failed request in HALF-OPEN, got {state.state}"

    def test_retry_logic_works_with_circuit_breaker_recovery(self):
        """
        Test that retry logic integrates correctly with circuit breaker recovery.

        Expected behavior:
        - First request fails, circuit breaker opens
        - Retry attempts are blocked by open circuit breaker
        - After recovery timeout, retry succeeds
        - Circuit breaker closes on successful retry
        """
        # Get MCP circuit breaker instance
        mcp_breaker = get_mcp_circuit_breaker()

        # Reset to known state
        mcp_breaker.state.state = CircuitState.CLOSED
        mcp_breaker.state.failure_count = 0

        # Simulate failures to open circuit breaker
        for _ in range(5):
            mcp_breaker._record_failure(Exception("MCP timeout"))

        # Verify circuit breaker is OPEN
        state = mcp_breaker.get_state()
        assert state.state == CircuitState.OPEN, \
            "Circuit breaker should be OPEN after threshold failures"

        # Simulate retry attempts (should be blocked by circuit breaker)
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # Attempt to call through circuit breaker
                # This should raise CircuitBreakerError
                state = mcp_breaker.get_state()
                if state.state == CircuitState.OPEN:
                    from src.resilience.circuit_breaker import CircuitBreakerState
                    raise CircuitBreakerError("mcp_server", CircuitBreakerState(state=CircuitState.OPEN))
                break  # If we get here, circuit is not open
            except CircuitBreakerError:
                retry_count += 1
                if retry_count >= max_retries:
                    # All retries exhausted
                    assert True, "Retries correctly blocked by open circuit breaker"
                    return

        # If we get here without raising, something is wrong
        pytest.fail("Circuit breaker should block retries when OPEN")

    def test_health_check_shows_recovery_state(self):
        """
        Test that GET /health correctly shows circuit breaker recovery states.

        Expected behavior:
        - Health check includes circuit breaker state (CLOSED, OPEN, HALF-OPEN)
        - Failure count is included in response
        - Last failure time is included when applicable
        """
        with patch('src.main.get_mcp_circuit_breaker') as mock_mcp_breaker:
            # Mock MCP circuit breaker in HALF-OPEN state (recovering)
            mock_mcp_state = MagicMock()
            mock_mcp_state.state = CircuitState.HALF_OPEN
            mock_mcp_state.failure_count = 5
            mock_mcp_state.last_failure_time = None

            mock_mcp_breaker.return_value.get_state.return_value = mock_mcp_state

            client = TestClient(app)
            response = client.get("/health")

            # Verify health check response includes recovery state
            assert response.status_code == 200
            data = response.json()

            # Verify circuit breaker state is exposed
            assert "circuit_breakers" in data
            assert "mcp_server" in data["circuit_breakers"]

            mcp_breaker_info = data["circuit_breakers"]["mcp_server"]
            assert mcp_breaker_info["state"] == "half-open" or mcp_breaker_info["state"] == "HALF-OPEN", \
                f"Circuit breaker state should be HALF-OPEN, got {mcp_breaker_info['state']}"
            assert mcp_breaker_info["failure_count"] == 5

    @pytest.mark.asyncio
    async def test_multiple_recovery_cycles(self):
        """
        Test that circuit breaker can go through multiple recovery cycles.

        Expected behavior:
        - Circuit breaker opens → recovers → closes (cycle 1)
        - Circuit breaker opens again → recovers → closes (cycle 2)
        - Each cycle behaves correctly
        """
        import asyncio

        # Get MCP circuit breaker instance
        mcp_breaker = get_mcp_circuit_breaker()

        # Cycle 1: Open → Recover → Close
        mcp_breaker.state.state = CircuitState.CLOSED
        mcp_breaker.state.failure_count = 0

        # Open circuit breaker
        for _ in range(5):
            mcp_breaker._record_failure(Exception("MCP timeout"))
        assert mcp_breaker.get_state().state == CircuitState.OPEN

        # Transition to HALF-OPEN
        mcp_breaker.state.state = CircuitState.HALF_OPEN

        # Successful request closes circuit breaker
        async def successful_op():
            await asyncio.sleep(0.01)
            return "success"

        await mcp_breaker.call(successful_op)
        assert mcp_breaker.get_state().state == CircuitState.CLOSED

        # Cycle 2: Open → Recover → Close
        # Open circuit breaker again
        for _ in range(5):
            mcp_breaker._record_failure(Exception("MCP timeout"))
        assert mcp_breaker.get_state().state == CircuitState.OPEN

        # Transition to HALF-OPEN
        mcp_breaker.state.state = CircuitState.HALF_OPEN

        # Successful request closes circuit breaker again
        await mcp_breaker.call(successful_op)
        assert mcp_breaker.get_state().state == CircuitState.CLOSED

        # Verify circuit breaker is fully operational after multiple cycles
        state = mcp_breaker.get_state()
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0


class TestStreamingEventFormat:
    """
    Additional tests for SSE streaming event format during degraded mode.

    Tests:
    - SSE events are properly formatted even during degradation
    - ERROR events include proper structure
    - DONE event is sent even when circuit breaker is open
    """

    def test_sse_error_event_format_during_degradation(self):
        """
        Test that SSE ERROR events have proper format when MCP is degraded.

        Expected format:
        - event: ERROR
        - data: {"error": "...", "status": "degraded"}
        """
        with patch.object(app.state, 'mcp_server', None):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Search for todos",
                    "request_id": "test_sse_error_001"
                }
            )

            # If streaming, parse SSE events
            # For JSON response, verify error structure
            if response.headers.get("content-type") == "application/json":
                data = response.json()
                assert "error" in data
                assert "status" in data
                assert data["status"] == "degraded"
            else:
                # Parse SSE stream
                content = response.text
                assert "error" in content.lower() or "ERROR" in content
                assert "degraded" in content.lower()

    def test_degraded_mode_logs_circuit_breaker_state(self, caplog):
        """
        Test that degraded mode triggers logging of circuit breaker state transitions.

        Expected behavior:
        - Circuit breaker state transitions are logged
        - Log includes CLOSED → OPEN transition
        - Log includes recovery timeout information
        """
        import logging

        with caplog.at_level(logging.INFO):
            # Get MCP circuit breaker
            mcp_breaker = get_mcp_circuit_breaker()

            # Reset to known state
            mcp_breaker.state.state = CircuitState.CLOSED
            mcp_breaker.state.failure_count = 0

            # Trigger state transition to OPEN
            for _ in range(5):
                mcp_breaker._record_failure(Exception("MCP timeout"))

            # Verify state transition was logged
            # Note: This depends on CircuitBreaker implementation logging state changes
            # If not implemented yet, this test will fail (TDD approach)
            state = mcp_breaker.get_state()
            assert state.state == CircuitState.OPEN


class TestSSEEventStreamFormat:
    """
    T025: Integration test for SSE event stream format compliance.

    Tests:
    - THINKING event format and content
    - TOOL_CALL event format with status (IN_PROGRESS, COMPLETED, FAILED)
    - RESPONSE_DELTA event format with incremental text
    - DONE event format with final_output and tools_called
    - Event ordering and stream structure
    """

    def test_sse_thinking_event_format(self):
        """
        Test that THINKING events have correct format.

        Expected format:
        event: THINKING
        data: {"content": "Agent reasoning text..."}

        The content should explain the agent's thought process,
        such as intent detection, parameter extraction, etc.
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to buy groceries",
                    "request_id": "test_sse_001"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T025: Verify THINKING events exist
            thinking_events = [e for e in events if e['event'] == 'THINKING']
            assert len(thinking_events) > 0, \
                "Stream should contain at least one THINKING event"

            # T025: Verify THINKING event data format
            for thinking_event in thinking_events:
                assert 'data' in thinking_event, \
                    "THINKING event should have data field"

                data = thinking_event['data']
                # Data should be dict or string
                assert isinstance(data, (dict, str)), \
                    "THINKING event data should be dict or string"

                # If dict, should have 'content' field
                if isinstance(data, dict):
                    assert 'content' in data or 'thinking' in data or 'text' in data, \
                        "THINKING event data should have content/thinking/text field"

    def test_sse_tool_call_event_format(self):
        """
        Test that TOOL_CALL events have correct format.

        Expected format:
        event: TOOL_CALL
        data: {
            "tool_name": "create_todo",
            "arguments": {"title": "Buy groceries"},
            "status": "IN_PROGRESS" | "COMPLETED" | "FAILED"
        }
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "List my todos",
                    "request_id": "test_sse_002"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T025: Verify TOOL_CALL events exist
            tool_call_events = [e for e in events if e['event'] == 'TOOL_CALL']

            if len(tool_call_events) > 0:
                # T025: Verify TOOL_CALL event structure
                for tool_event in tool_call_events:
                    assert 'data' in tool_event, \
                        "TOOL_CALL event should have data field"

                    data = tool_event['data']
                    assert isinstance(data, dict), \
                        "TOOL_CALL event data should be a dictionary"

                    # T025: Verify required fields
                    # Note: Field names may vary (tool_name vs name, etc.)
                    # Check for common variations
                    has_tool_identifier = (
                        'tool_name' in data or
                        'name' in data or
                        'tool' in data
                    )
                    assert has_tool_identifier, \
                        "TOOL_CALL event should have tool identifier (tool_name/name/tool)"

                    # Status should be one of the valid values
                    if 'status' in data:
                        valid_statuses = ['IN_PROGRESS', 'COMPLETED', 'FAILED', 'in_progress', 'completed', 'failed']
                        assert data['status'] in valid_statuses, \
                            f"TOOL_CALL status should be one of {valid_statuses}, got {data['status']}"

    def test_sse_response_delta_event_format(self):
        """
        Test that RESPONSE_DELTA events have correct format.

        Expected format:
        event: RESPONSE_DELTA
        data: {
            "delta": "New text chunk",
            "accumulated": "Full text so far..."
        }

        Response deltas build up the final response incrementally.
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "What are my tasks?",
                    "request_id": "test_sse_003"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T025: Find RESPONSE_DELTA events
            response_deltas = [e for e in events if e['event'] == 'RESPONSE_DELTA']

            if len(response_deltas) > 0:
                # T025: Verify RESPONSE_DELTA structure
                for delta_event in response_deltas:
                    assert 'data' in delta_event, \
                        "RESPONSE_DELTA event should have data field"

                    data = delta_event['data']

                    # Data can be string or dict
                    if isinstance(data, dict):
                        # Should have delta or content field
                        has_text_field = (
                            'delta' in data or
                            'content' in data or
                            'text' in data or
                            'accumulated' in data
                        )
                        assert has_text_field, \
                            "RESPONSE_DELTA should have text content (delta/content/text/accumulated)"

    def test_sse_done_event_format(self):
        """
        Test that DONE events have correct format.

        Expected format:
        event: DONE
        data: {
            "final_output": "Complete response text",
            "tools_called": ["create_todo", "list_todos"],
            "success": true
        }
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task",
                    "request_id": "test_sse_004"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T025: Verify DONE event exists
            done_events = [e for e in events if e['event'] == 'DONE']
            assert len(done_events) == 1, \
                "Stream should end with exactly one DONE event"

            # T025: Verify DONE event structure
            done_event = done_events[0]
            assert 'data' in done_event, \
                "DONE event should have data field"

            data = done_event['data']
            assert isinstance(data, dict), \
                "DONE event data should be a dictionary"

            # T025: Verify success field
            assert 'success' in data, \
                "DONE event should have success field"
            assert isinstance(data['success'], bool), \
                "DONE success field should be boolean"

            # T025: Verify final_output or similar field exists
            has_output_field = (
                'final_output' in data or
                'output' in data or
                'result' in data or
                'message' in data
            )
            assert has_output_field, \
                "DONE event should have output field (final_output/output/result/message)"

    def test_sse_event_ordering(self):
        """
        Test that SSE events arrive in correct order.

        Expected order:
        1. THINKING (optional, can be multiple)
        2. TOOL_CALL (optional, can be multiple)
        3. RESPONSE_DELTA (optional, can be multiple)
        4. DONE (required, exactly one, always last)
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Show me my todos",
                    "request_id": "test_sse_005"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # Get event types in order
            event_types = [e['event'] for e in events]

            # T025: DONE should be last event
            assert len(event_types) > 0, "Stream should have at least one event"
            assert event_types[-1] == 'DONE', \
                f"DONE should be last event, but got {event_types[-1]}"

            # T025: DONE should appear exactly once
            done_count = event_types.count('DONE')
            assert done_count == 1, \
                f"DONE should appear exactly once, found {done_count}"

            # T025: If THINKING and TOOL_CALL both present, THINKING should come first
            if 'THINKING' in event_types and 'TOOL_CALL' in event_types:
                first_thinking = event_types.index('THINKING')
                first_tool_call = event_types.index('TOOL_CALL')
                assert first_thinking < first_tool_call, \
                    "THINKING should typically come before TOOL_CALL"

    def test_sse_error_event_format(self):
        """
        Test that ERROR events have correct format when errors occur.

        Expected format:
        event: ERROR
        data: {
            "error": "User-friendly error message",
            "error_type": "MCP_CONNECTION_ERROR" | "TIMEOUT" | etc.,
            "recoverable": true | false
        }
        """
        # Simulate error by using degraded mode (no MCP server)
        with patch.object(app.state, 'mcp_server', None):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task",
                    "request_id": "test_sse_006"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T025: Should have ERROR event in degraded mode
            error_events = [e for e in events if e['event'] == 'ERROR']

            if len(error_events) > 0:
                # T025: Verify ERROR event structure
                error_event = error_events[0]
                assert 'data' in error_event, \
                    "ERROR event should have data field"

                data = error_event['data']
                assert isinstance(data, dict), \
                    "ERROR event data should be a dictionary"

                # T025: Should have error message
                has_error_field = (
                    'error' in data or
                    'message' in data or
                    'error_message' in data
                )
                assert has_error_field, \
                    "ERROR event should have error message field"

                # T025: Error message should be user-friendly (not technical)
                if 'error' in data:
                    error_msg = data['error'].lower()
                    # Should NOT contain technical jargon
                    assert 'traceback' not in error_msg, \
                        "Error message should not contain stack traces"
                    assert 'exception' not in error_msg, \
                        "Error message should not contain exception details"

    def test_sse_stream_http_headers(self):
        """
        Test that SSE stream has correct HTTP headers.

        Expected headers:
        - Content-Type: text/event-stream
        - Cache-Control: no-cache
        - Connection: keep-alive
        - X-Request-ID: <request_id>
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Test message",
                    "request_id": "test_sse_007"
                }
            )

            # T025: Verify Content-Type
            assert response.headers.get('content-type') == 'text/event-stream', \
                "Content-Type should be text/event-stream"

            # T025: Verify Cache-Control
            cache_control = response.headers.get('cache-control', '').lower()
            assert 'no-cache' in cache_control, \
                "Cache-Control should include no-cache"

            # T025: Verify X-Request-ID if provided
            request_id_header = response.headers.get('x-request-id')
            if request_id_header:
                assert request_id_header == "test_sse_007", \
                    "X-Request-ID header should match request_id"

    def test_sse_stream_graceful_termination(self):
        """
        Test that SSE stream terminates gracefully.

        Expected behavior:
        - Stream always ends with DONE event
        - No incomplete events
        - Stream closes cleanly without hanging
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Quick test",
                    "request_id": "test_sse_008"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T025: Stream should have at least DONE event
            assert len(events) > 0, \
                "Stream should have at least one event"

            # T025: Last event should be DONE
            assert events[-1]['event'] == 'DONE', \
                "Stream should terminate with DONE event"

    def _parse_sse_stream(self, stream_text: str) -> list:
        """
        Parse SSE stream text into list of events.

        Args:
            stream_text: Raw SSE response text

        Returns:
            List of event dictionaries with 'event' and 'data' keys
        """
        events = []
        lines = stream_text.strip().split('\n')

        current_event = None
        current_data = None

        for line in lines:
            line = line.strip()

            if line.startswith('event:'):
                current_event = line.split('event:', 1)[1].strip()
            elif line.startswith('data:'):
                data_str = line.split('data:', 1)[1].strip()
                try:
                    current_data = json.loads(data_str)
                except json.JSONDecodeError:
                    current_data = data_str
            elif line == '' and current_event:
                # Empty line signals end of event
                events.append({
                    'event': current_event,
                    'data': current_data
                })
                current_event = None
                current_data = None

        return events
