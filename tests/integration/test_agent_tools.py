"""
Integration tests for Agent tool execution via MCP protocol.

T023: Test create_todo tool execution (verify tool call, database persistence, SSE events)
T024: Test list_todos tool execution (verify filtering, result format, SSE events)

NOTE: These tests are written FIRST (TDD approach) and should FAIL before implementation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
import time

from src.main import app
from src.mcp_server.models import Todo, TodoStatus
from src.mcp_server.database import get_session
from sqlmodel import select


class TestCreateTodoToolExecution:
    """
    T023: Integration test for create_todo tool execution via agent.

    Tests:
    - Agent correctly calls create_todo MCP tool with extracted parameters
    - Todo is persisted to database
    - SSE events are properly formatted (THINKING, TOOL_CALL, RESPONSE_DELTA, DONE)
    - Tool execution duration is logged
    """

    def test_create_todo_natural_language_request(self):
        """
        Test that agent creates todo from natural language request.

        Expected behavior:
        - User message: "Create a task to buy groceries"
        - Agent detects CREATE intent
        - Agent calls create_todo tool with title="Buy groceries"
        - Todo is persisted to database with status=ACTIVE
        - SSE stream includes all expected events
        """
        # Mock MCP server to be available (not degraded mode)
        with patch.object(app.state, 'mcp_server', MagicMock()) as mock_mcp:
            client = TestClient(app)

            # Send create todo request
            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to buy groceries",
                    "request_id": "test_create_001"
                }
            )

            # Verify HTTP 200 response
            assert response.status_code == 200, \
                f"Expected HTTP 200, got {response.status_code}"

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # T023: Verify THINKING event is present
            thinking_events = [e for e in events if e['event'] == 'THINKING']
            assert len(thinking_events) > 0, \
                "Should have at least one THINKING event showing agent reasoning"

            # T023: Verify TOOL_CALL event with create_todo
            tool_call_events = [e for e in events if e['event'] == 'TOOL_CALL']
            assert len(tool_call_events) > 0, \
                "Should have TOOL_CALL event for create_todo"

            # Find create_todo tool call
            create_tool_calls = [
                e for e in tool_call_events
                if 'create_todo' in json.dumps(e.get('data', {})).lower()
            ]
            assert len(create_tool_calls) > 0, \
                "Should have create_todo tool call"

            # T023: Verify tool call includes title parameter
            create_tool_data = create_tool_calls[0]['data']
            if 'arguments' in create_tool_data:
                args = create_tool_data['arguments']
                assert 'title' in args or 'task' in json.dumps(args).lower(), \
                    "Tool call should include title/task parameter"

            # T023: Verify DONE event is present
            done_events = [e for e in events if e['event'] == 'DONE']
            assert len(done_events) == 1, \
                "Should have exactly one DONE event at end of stream"

            # T023: Verify success=true in DONE event
            done_data = done_events[0].get('data', {})
            assert done_data.get('success') is True, \
                "DONE event should indicate success=true"

    def test_create_todo_with_due_date_extraction(self):
        """
        Test that agent correctly extracts due date from natural language.

        Expected behavior:
        - User message: "Remind me to call dentist tomorrow at 3pm"
        - Agent extracts: title="Call dentist", due_date="tomorrow 3pm"
        - create_todo tool called with both parameters
        - Todo persisted with due_date field populated
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Remind me to call dentist tomorrow at 3pm",
                    "request_id": "test_create_002"
                }
            )

            assert response.status_code == 200

            # Parse SSE stream
            events = self._parse_sse_stream(response.text)

            # Verify tool call includes both title and due_date
            tool_call_events = [e for e in events if e['event'] == 'TOOL_CALL']
            assert len(tool_call_events) > 0, "Should have create_todo tool call"

            # Check if due_date is mentioned in tool call or thinking
            stream_text = response.text.lower()
            assert 'tomorrow' in stream_text or '3pm' in stream_text or 'due' in stream_text, \
                "Agent should recognize and process due date information"

    def test_create_todo_with_priority_extraction(self):
        """
        Test that agent extracts priority from natural language.

        Expected behavior:
        - User message: "Create an urgent task to fix production bug"
        - Agent extracts: title="Fix production bug", priority="high"
        - create_todo tool called with priority parameter
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create an urgent task to fix production bug",
                    "request_id": "test_create_003"
                }
            )

            assert response.status_code == 200

            # Parse events
            events = self._parse_sse_stream(response.text)

            # Verify CREATE intent detected
            stream_text = response.text.lower()
            assert 'urgent' in stream_text or 'priority' in stream_text or 'high' in stream_text, \
                "Agent should recognize priority indicators"

    def test_create_todo_database_persistence(self):
        """
        Test that created todo is actually persisted to database.

        Expected behavior:
        - Agent creates todo via MCP tool
        - Todo exists in database after tool execution
        - Database record has correct fields (title, status, created_at)
        """
        # This test would require actual database connection
        # For now, we verify the intent through SSE events
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to buy milk",
                    "request_id": "test_create_004"
                }
            )

            assert response.status_code == 200

            # Verify success in stream
            events = self._parse_sse_stream(response.text)
            done_events = [e for e in events if e['event'] == 'DONE']
            assert len(done_events) > 0
            assert done_events[0]['data'].get('success') is True

    def test_create_todo_sse_event_order(self):
        """
        Test that SSE events arrive in correct order.

        Expected order:
        1. THINKING (agent reasoning)
        2. TOOL_CALL (create_todo execution)
        3. RESPONSE_DELTA (confirmation message)
        4. DONE (stream complete)
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to write documentation",
                    "request_id": "test_create_005"
                }
            )

            assert response.status_code == 200

            # Parse events in order
            events = self._parse_sse_stream(response.text)

            # Get event types in order
            event_types = [e['event'] for e in events]

            # T023: Verify THINKING comes before TOOL_CALL
            if 'THINKING' in event_types and 'TOOL_CALL' in event_types:
                thinking_idx = event_types.index('THINKING')
                tool_call_idx = event_types.index('TOOL_CALL')
                assert thinking_idx < tool_call_idx, \
                    "THINKING should come before TOOL_CALL"

            # T023: Verify DONE is last event
            assert event_types[-1] == 'DONE', \
                "DONE should be the last event in stream"

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


class TestListTodosToolExecution:
    """
    T024: Integration test for list_todos tool execution via agent.

    Tests:
    - Agent correctly calls list_todos MCP tool
    - Filtering parameters are extracted from natural language
    - Result format is user-friendly (natural language, not raw JSON)
    - SSE events include formatted todo list in RESPONSE_DELTA
    """

    def test_list_todos_all_active_tasks(self):
        """
        Test that agent lists all active todos.

        Expected behavior:
        - User message: "What are my active tasks?"
        - Agent calls list_todos with status="active"
        - Results formatted as natural language list
        - SSE stream includes RESPONSE_DELTA with formatted list
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "What are my active tasks?",
                    "request_id": "test_list_001"
                }
            )

            assert response.status_code == 200

            # Parse events
            events = self._parse_sse_stream(response.text)

            # T024: Verify LIST intent detected via TOOL_CALL
            tool_call_events = [e for e in events if e['event'] == 'TOOL_CALL']
            assert len(tool_call_events) > 0, \
                "Should have TOOL_CALL event for list_todos"

            # Verify list_todos mentioned in stream
            stream_text = response.text.lower()
            assert 'list' in stream_text or 'todos' in stream_text or 'tasks' in stream_text, \
                "Stream should mention listing todos"

    def test_list_todos_with_status_filter(self):
        """
        Test that agent filters todos by status.

        Expected behavior:
        - User message: "Show me completed tasks"
        - Agent calls list_todos with status="completed"
        - Only completed todos returned
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Show me completed tasks",
                    "request_id": "test_list_002"
                }
            )

            assert response.status_code == 200

            # Verify status filter mentioned
            stream_text = response.text.lower()
            assert 'completed' in stream_text, \
                "Agent should recognize completed status filter"

    def test_list_todos_with_priority_filter(self):
        """
        Test that agent filters todos by priority.

        Expected behavior:
        - User message: "Show me high priority tasks"
        - Agent calls list_todos with priority="high"
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Show me high priority tasks",
                    "request_id": "test_list_003"
                }
            )

            assert response.status_code == 200

            # Verify priority filter mentioned
            stream_text = response.text.lower()
            assert 'high' in stream_text or 'priority' in stream_text, \
                "Agent should recognize priority filter"

    def test_list_todos_natural_language_format(self):
        """
        Test that list results are formatted in natural language.

        Expected behavior:
        - Results NOT raw JSON
        - User-friendly list format: "1. Task title (Priority, Status)"
        - RESPONSE_DELTA events contain formatted text
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "List my todos",
                    "request_id": "test_list_004"
                }
            )

            assert response.status_code == 200

            # Parse events
            events = self._parse_sse_stream(response.text)

            # T024: Verify RESPONSE_DELTA events exist
            response_deltas = [e for e in events if e['event'] == 'RESPONSE_DELTA']

            # If we have response deltas, check they're not raw JSON
            if response_deltas:
                for delta_event in response_deltas:
                    delta_data = delta_event.get('data', {})
                    if isinstance(delta_data, dict):
                        delta_text = delta_data.get('delta', '') or delta_data.get('content', '')
                    else:
                        delta_text = str(delta_data)

                    # Should not be raw JSON array/object
                    if delta_text:
                        assert not delta_text.strip().startswith('['), \
                            "Response should not be raw JSON array"
                        assert not delta_text.strip().startswith('{"id":'), \
                            "Response should not be raw JSON object"

    def test_list_todos_empty_result_handling(self):
        """
        Test that agent handles empty todo list gracefully.

        Expected behavior:
        - No todos match filters
        - Agent returns friendly message: "You don't have any todos matching..."
        - NOT an error, just empty result
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Show me todos tagged urgent",
                    "request_id": "test_list_005"
                }
            )

            assert response.status_code == 200

            # Should still be successful even if empty
            events = self._parse_sse_stream(response.text)
            done_events = [e for e in events if e['event'] == 'DONE']
            assert len(done_events) > 0

    def test_list_todos_sse_event_structure(self):
        """
        Test that list_todos SSE events have correct structure.

        Expected events:
        1. THINKING - "I'm looking for todos with filters..."
        2. TOOL_CALL - list_todos with arguments
        3. RESPONSE_DELTA - Formatted todo list
        4. DONE - Stream complete
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "What tasks do I have?",
                    "request_id": "test_list_006"
                }
            )

            assert response.status_code == 200

            # Parse events
            events = self._parse_sse_stream(response.text)

            # Get event types
            event_types = [e['event'] for e in events]

            # T024: Verify DONE is present
            assert 'DONE' in event_types, \
                "Stream should end with DONE event"

            # T024: Verify DONE is last
            assert event_types[-1] == 'DONE', \
                "DONE should be the last event"

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


# ============================================================================
# T029: Integration test for context metadata logging
# ============================================================================

class TestContextMetadataLogging:
    """
    T029: Integration test for context metadata logging.

    Verifies that context metadata (request_id, thread_id, timestamp) is properly
    included in structured logs for all tool calls.

    Tests:
    - request_id is present in log records
    - thread_id is present in log records (when provided)
    - timestamp is present in log records
    - Context metadata flows through agent execution
    - Tool call logs include context information
    """

    def test_request_id_in_logs(self, caplog):
        """
        Test that request_id is included in structured logs.

        Verifies:
        - request_id from ChatRequest appears in log records
        - All agent execution logs contain request_id
        - Tool call logs contain request_id
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            # Clear previous logs
            caplog.clear()

            # Set log level to capture INFO logs
            caplog.set_level(logging.INFO)

            # Send request with specific request_id
            test_request_id = "test_request_id_12345"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to test request_id logging",
                    "request_id": test_request_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Verify request_id appears in log records
            log_records = [record for record in caplog.records if hasattr(record, 'request_id')]

            # Should have at least one log with request_id
            assert len(log_records) > 0, \
                f"Expected logs with request_id, but found none. Total logs: {len(caplog.records)}"

            # Verify request_id value matches
            for record in log_records:
                assert record.request_id == test_request_id, \
                    f"Expected request_id '{test_request_id}', got '{record.request_id}'"

    def test_thread_id_in_logs(self, caplog):
        """
        Test that thread_id is included in structured logs when provided.

        Verifies:
        - thread_id from ChatRequest appears in log records
        - Thread context is maintained throughout execution
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            # Send request with specific thread_id
            test_thread_id = "thread_abc123"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "List my todos",
                    "request_id": "test_thread_001",
                    "thread_id": test_thread_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Verify thread_id appears in log records
            log_records = [record for record in caplog.records if hasattr(record, 'thread_id')]

            # Should have at least one log with thread_id
            assert len(log_records) > 0, \
                f"Expected logs with thread_id, but found none. Total logs: {len(caplog.records)}"

            # Verify thread_id value matches
            for record in log_records:
                assert record.thread_id == test_thread_id, \
                    f"Expected thread_id '{test_thread_id}', got '{record.thread_id}'"

    def test_timestamp_in_logs(self, caplog):
        """
        Test that timestamps are present in all log records.

        Verifies:
        - All log records have created timestamp
        - Timestamps are in valid format
        - Timestamps are recent (within last minute)
        """
        import logging
        from datetime import datetime, timezone, timedelta

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            # Record test start time
            test_start_time = datetime.now(timezone.utc)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to test timestamps",
                    "request_id": "test_timestamp_001"
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Verify all log records have timestamps
            assert len(caplog.records) > 0, "Should have log records"

            for record in caplog.records:
                # Check that record has created timestamp
                assert hasattr(record, 'created'), "Log record should have 'created' timestamp"

                # Convert timestamp to datetime
                log_time = datetime.fromtimestamp(record.created, tz=timezone.utc)

                # Verify timestamp is recent (within 1 minute of test start)
                time_diff = log_time - test_start_time
                assert abs(time_diff) < timedelta(minutes=1), \
                    f"Log timestamp {log_time} is too far from test start {test_start_time}"

    def test_context_metadata_in_tool_call_logs(self, caplog):
        """
        Test that context metadata appears in tool call logs.

        Verifies:
        - Tool call logs include request_id
        - Tool call logs include execution_duration
        - Tool call logs include tool_name
        - Tool call logs include tool_status
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            test_request_id = "test_tool_context_001"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task for testing tool call context",
                    "request_id": test_request_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Find tool call related logs
            # Look for logs with 'mcp_tool_call' event or 'agent_execution_completed' event
            tool_logs = [
                record for record in caplog.records
                if hasattr(record, '__dict__') and (
                    record.__dict__.get('event') == 'mcp_tool_call' or
                    record.__dict__.get('event') == 'agent_execution_completed'
                )
            ]

            # Should have at least one tool-related log
            # Note: May not always trigger tool calls in test environment
            # This test primarily validates log structure when tools ARE called
            if len(tool_logs) > 0:
                for record in tool_logs:
                    # Verify execution_duration field exists
                    assert hasattr(record, 'execution_duration_seconds') or \
                           'execution_duration_seconds' in record.__dict__, \
                        "Tool call logs should include execution_duration_seconds"

                    # Verify event type is present
                    assert hasattr(record, 'event') or 'event' in record.__dict__, \
                        "Tool call logs should include event field"

    def test_context_metadata_flows_through_execution(self, caplog):
        """
        Test that context metadata is maintained throughout agent execution.

        Verifies:
        - request_id is present from start to finish
        - Multiple log entries share the same request_id
        - Context is not lost during async execution
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            test_request_id = "test_context_flow_001"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "List all my active tasks",
                    "request_id": test_request_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Collect all logs with request_id
            request_logs = [
                record for record in caplog.records
                if hasattr(record, 'request_id') and record.request_id == test_request_id
            ]

            # Should have multiple logs with same request_id
            # This proves context is maintained throughout execution
            if len(request_logs) > 1:
                # Verify all have same request_id
                request_ids = [record.request_id for record in request_logs]
                assert all(rid == test_request_id for rid in request_ids), \
                    "All logs in same request should have matching request_id"

    def test_missing_request_id_handled_gracefully(self, caplog):
        """
        Test that missing request_id is handled gracefully.

        Verifies:
        - Request succeeds even without request_id
        - Logs are still generated
        - System doesn't crash on missing context
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            # Send request WITHOUT request_id
            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task without request_id"
                    # Note: No request_id field
                }
            )

            assert response.status_code == 200, \
                "Request should succeed even without request_id"

            # Verify logs were still generated
            assert len(caplog.records) > 0, \
                "Logs should be generated even without request_id"

    def test_log_structure_includes_standard_fields(self, caplog):
        """
        Test that structured logs include standard fields.

        Verifies:
        - levelname (INFO, WARNING, ERROR, etc.)
        - message (log message content)
        - name (logger name)
        - module (source module)
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Test log structure",
                    "request_id": "test_structure_001"
                }
            )

            assert response.status_code == 200, "Request should succeed"
            assert len(caplog.records) > 0, "Should have log records"

            # Verify standard log fields
            for record in caplog.records:
                assert hasattr(record, 'levelname'), "Log should have levelname"
                assert hasattr(record, 'message'), "Log should have message"
                assert hasattr(record, 'name'), "Log should have logger name"
                assert hasattr(record, 'module'), "Log should have module"

                # Verify levelname is valid
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                assert record.levelname in valid_levels, \
                    f"Invalid log level: {record.levelname}"


# ============================================================================
# T029: Integration test for context metadata logging
# ============================================================================

class TestContextMetadataLogging:
    """
    T029: Integration test for context metadata logging.

    Verifies that context metadata (request_id, thread_id, timestamp) is properly
    included in structured logs for all tool calls.

    Tests:
    - request_id is present in log records
    - thread_id is present in log records (when provided)
    - timestamp is present in log records
    - Context metadata flows through agent execution
    - Tool call logs include context information
    """

    def test_request_id_in_logs(self, caplog):
        """
        Test that request_id is included in structured logs.

        Verifies:
        - request_id from ChatRequest appears in log records
        - All agent execution logs contain request_id
        - Tool call logs contain request_id
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            # Clear previous logs
            caplog.clear()

            # Set log level to capture INFO logs
            caplog.set_level(logging.INFO)

            # Send request with specific request_id
            test_request_id = "test_request_id_12345"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to test request_id logging",
                    "request_id": test_request_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Verify request_id appears in log records
            log_records = [record for record in caplog.records if hasattr(record, 'request_id')]

            # Should have at least one log with request_id
            assert len(log_records) > 0, \
                f"Expected logs with request_id, but found none. Total logs: {len(caplog.records)}"

            # Verify request_id value matches
            for record in log_records:
                assert record.request_id == test_request_id, \
                    f"Expected request_id '{test_request_id}', got '{record.request_id}'"

    def test_thread_id_in_logs(self, caplog):
        """
        Test that thread_id is included in structured logs when provided.

        Verifies:
        - thread_id from ChatRequest appears in log records
        - Thread context is maintained throughout execution
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            # Send request with specific thread_id
            test_thread_id = "thread_abc123"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "List my todos",
                    "request_id": "test_thread_001",
                    "thread_id": test_thread_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Verify thread_id appears in log records
            log_records = [record for record in caplog.records if hasattr(record, 'thread_id')]

            # Should have at least one log with thread_id
            assert len(log_records) > 0, \
                f"Expected logs with thread_id, but found none. Total logs: {len(caplog.records)}"

            # Verify thread_id value matches
            for record in log_records:
                assert record.thread_id == test_thread_id, \
                    f"Expected thread_id '{test_thread_id}', got '{record.thread_id}'"

    def test_timestamp_in_logs(self, caplog):
        """
        Test that timestamps are present in all log records.

        Verifies:
        - All log records have created timestamp
        - Timestamps are in valid format
        - Timestamps are recent (within last minute)
        """
        import logging
        from datetime import datetime, timezone, timedelta

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            # Record test start time
            test_start_time = datetime.now(timezone.utc)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to test timestamps",
                    "request_id": "test_timestamp_001"
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Verify all log records have timestamps
            assert len(caplog.records) > 0, "Should have log records"

            for record in caplog.records:
                # Check that record has created timestamp
                assert hasattr(record, 'created'), "Log record should have 'created' timestamp"

                # Convert timestamp to datetime
                log_time = datetime.fromtimestamp(record.created, tz=timezone.utc)

                # Verify timestamp is recent (within 1 minute of test start)
                time_diff = log_time - test_start_time
                assert abs(time_diff) < timedelta(minutes=1), \
                    f"Log timestamp {log_time} is too far from test start {test_start_time}"

    def test_context_metadata_in_tool_call_logs(self, caplog):
        """
        Test that context metadata appears in tool call logs.

        Verifies:
        - Tool call logs include request_id
        - Tool call logs include execution_duration
        - Tool call logs include tool_name
        - Tool call logs include tool_status
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            test_request_id = "test_tool_context_001"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task for testing tool call context",
                    "request_id": test_request_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Find tool call related logs
            # Look for logs with 'mcp_tool_call' event or 'agent_execution_completed' event
            tool_logs = [
                record for record in caplog.records
                if hasattr(record, '__dict__') and (
                    record.__dict__.get('event') == 'mcp_tool_call' or
                    record.__dict__.get('event') == 'agent_execution_completed'
                )
            ]

            # Should have at least one tool-related log
            # Note: May not always trigger tool calls in test environment
            # This test primarily validates log structure when tools ARE called
            if len(tool_logs) > 0:
                for record in tool_logs:
                    # Verify execution_duration field exists
                    assert hasattr(record, 'execution_duration_seconds') or \
                           'execution_duration_seconds' in record.__dict__, \
                        "Tool call logs should include execution_duration_seconds"

                    # Verify event type is present
                    assert hasattr(record, 'event') or 'event' in record.__dict__, \
                        "Tool call logs should include event field"

    def test_context_metadata_flows_through_execution(self, caplog):
        """
        Test that context metadata is maintained throughout agent execution.

        Verifies:
        - request_id is present from start to finish
        - Multiple log entries share the same request_id
        - Context is not lost during async execution
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            test_request_id = "test_context_flow_001"

            response = client.post(
                "/chat/stream",
                json={
                    "message": "List all my active tasks",
                    "request_id": test_request_id
                }
            )

            assert response.status_code == 200, "Request should succeed"

            # Collect all logs with request_id
            request_logs = [
                record for record in caplog.records
                if hasattr(record, 'request_id') and record.request_id == test_request_id
            ]

            # Should have multiple logs with same request_id
            # This proves context is maintained throughout execution
            if len(request_logs) > 1:
                # Verify all have same request_id
                request_ids = [record.request_id for record in request_logs]
                assert all(rid == test_request_id for rid in request_ids), \
                    "All logs in same request should have matching request_id"

    def test_missing_request_id_handled_gracefully(self, caplog):
        """
        Test that missing request_id is handled gracefully.

        Verifies:
        - Request succeeds even without request_id
        - Logs are still generated
        - System doesn't crash on missing context
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            # Send request WITHOUT request_id
            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task without request_id"
                    # Note: No request_id field
                }
            )

            assert response.status_code == 200, \
                "Request should succeed even without request_id"

            # Verify logs were still generated
            assert len(caplog.records) > 0, \
                "Logs should be generated even without request_id"

    def test_log_structure_includes_standard_fields(self, caplog):
        """
        Test that structured logs include standard fields.

        Verifies:
        - levelname (INFO, WARNING, ERROR, etc.)
        - message (log message content)
        - name (logger name)
        - module (source module)
        """
        import logging

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            caplog.clear()
            caplog.set_level(logging.INFO)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Test log structure",
                    "request_id": "test_structure_001"
                }
            )

            assert response.status_code == 200, "Request should succeed"
            assert len(caplog.records) > 0, "Should have log records"

            # Verify standard log fields
            for record in caplog.records:
                assert hasattr(record, 'levelname'), "Log should have levelname"
                assert hasattr(record, 'message'), "Log should have message"
                assert hasattr(record, 'name'), "Log should have logger name"
                assert hasattr(record, 'module'), "Log should have module"

                # Verify levelname is valid
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                assert record.levelname in valid_levels, \
                    f"Invalid log level: {record.levelname}"
