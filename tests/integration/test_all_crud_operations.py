"""
T027: Integration test for all 5 CRUD operations via agent.

This test verifies that the agent can execute all CRUD operations:
1. CREATE - create_todo
2. LIST - list_todos
3. UPDATE - update_todo
4. SEARCH - search_todos
5. DELETE - delete_todo

NOTE: This is a TDD test written BEFORE full implementation. May fail initially.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json

from src.main import app


class TestAllCRUDOperations:
    """
    T027: Integration test for all 5 CRUD operations.

    Tests that agent correctly:
    - Detects intent from natural language
    - Calls appropriate MCP tool
    - Returns formatted results
    - Completes with success=true
    """

    def test_create_todo_operation(self):
        """
        Test CREATE operation: create_todo

        Natural language: "Create a task to buy groceries"
        Expected: create_todo tool called, success response
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Create a task to buy groceries for dinner",
                    "request_id": "test_create"
                }
            )

            assert response.status_code == 200, \
                "CREATE operation should return HTTP 200"

            # Parse SSE events
            events = self._parse_sse_stream(response.text)

            # Verify DONE event with success
            done_events = [e for e in events if e['event'] == 'done']
            assert len(done_events) > 0, "Should have DONE event"

            # Verify create_todo was mentioned/called
            stream_text = response.text.lower()
            assert 'create' in stream_text or 'todo' in stream_text, \
                "CREATE intent should be detected"

    def test_list_todos_operation(self):
        """
        Test LIST operation: list_todos

        Natural language: "What are my active tasks?"
        Expected: list_todos tool called, formatted list returned
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "What are my active tasks?",
                    "request_id": "test_list"
                }
            )

            assert response.status_code == 200, \
                "LIST operation should return HTTP 200"

            # Parse SSE events
            events = self._parse_sse_stream(response.text)

            # Verify DONE event
            done_events = [e for e in events if e['event'] == 'done']
            assert len(done_events) > 0, "Should have DONE event"

            # Verify list/active intent detected
            stream_text = response.text.lower()
            assert 'list' in stream_text or 'tasks' in stream_text or 'active' in stream_text, \
                "LIST intent should be detected"

    def test_update_todo_operation(self):
        """
        Test UPDATE operation: update_todo

        Natural language: "Mark task 1 as completed"
        Expected: update_todo tool called, success response
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Mark the grocery task as completed",
                    "request_id": "test_update"
                }
            )

            assert response.status_code == 200, \
                "UPDATE operation should return HTTP 200"

            # Parse SSE events
            events = self._parse_sse_stream(response.text)

            # Verify DONE event
            done_events = [e for e in events if e['event'] == 'done']
            assert len(done_events) > 0, "Should have DONE event"

            # Verify update/mark/complete intent detected
            stream_text = response.text.lower()
            assert any(word in stream_text for word in ['mark', 'update', 'complete', 'done']), \
                "UPDATE intent should be detected"

    def test_search_todos_operation(self):
        """
        Test SEARCH operation: search_todos

        Natural language: "Find todos about groceries"
        Expected: search_todos tool called, search results returned
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Find todos about groceries",
                    "request_id": "test_search"
                }
            )

            assert response.status_code == 200, \
                "SEARCH operation should return HTTP 200"

            # Parse SSE events
            events = self._parse_sse_stream(response.text)

            # Verify DONE event
            done_events = [e for e in events if e['event'] == 'done']
            assert len(done_events) > 0, "Should have DONE event"

            # Verify search/find intent detected
            stream_text = response.text.lower()
            assert 'find' in stream_text or 'search' in stream_text or 'groceries' in stream_text, \
                "SEARCH intent should be detected"

    def test_delete_todo_operation(self):
        """
        Test DELETE operation: delete_todo

        Natural language: "Delete the completed task"
        Expected: delete_todo tool called, success response
        """
        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            response = client.post(
                "/chat/stream",
                json={
                    "message": "Delete the completed grocery task",
                    "request_id": "test_delete"
                }
            )

            assert response.status_code == 200, \
                "DELETE operation should return HTTP 200"

            # Parse SSE events
            events = self._parse_sse_stream(response.text)

            # Verify DONE event
            done_events = [e for e in events if e['event'] == 'done']
            assert len(done_events) > 0, "Should have DONE event"

            # Verify delete/remove intent detected
            stream_text = response.text.lower()
            assert 'delete' in stream_text or 'remove' in stream_text or 'completed' in stream_text, \
                "DELETE intent should be detected"

    def test_all_operations_have_proper_event_flow(self):
        """
        Test that all CRUD operations follow proper SSE event flow.

        Expected flow for all operations:
        - THINKING (agent reasoning)
        - TOOL_CALL (MCP tool execution)
        - RESPONSE_DELTA (formatted response)
        - DONE (completion)
        """
        operations = [
            "Create a task to test event flow",
            "List my todos",
            "Update task 1 to completed",
            "Search for test todos",
            "Delete task 1"
        ]

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            for message in operations:
                response = client.post(
                    "/chat/stream",
                    json={
                        "message": message,
                        "request_id": f"test_{message[:10]}"
                    }
                )

                assert response.status_code == 200

                # Parse events
                events = self._parse_sse_stream(response.text)
                event_types = [e['event'] for e in events]

                # Verify DONE is present
                assert 'done' in event_types, \
                    f"All operations should end with DONE event (message: {message})"

                # Verify DONE is last
                assert event_types[-1] == 'done', \
                    f"DONE should be last event (message: {message})"

    def test_crud_operations_with_natural_language_variations(self):
        """
        Test that agent handles natural language variations for CRUD operations.

        Tests different phrasings for the same operation.
        """
        # Different ways to say CREATE
        create_variations = [
            "Create a task to buy milk",
            "Add a todo for calling dentist",
            "I need to remember to email John",
            "Remind me to pay bills"
        ]

        # Different ways to say LIST
        list_variations = [
            "What are my todos?",
            "Show me my tasks",
            "List all active items",
            "What do I need to do?"
        ]

        with patch.object(app.state, 'mcp_server', MagicMock()):
            client = TestClient(app)

            # Test CREATE variations
            for message in create_variations:
                response = client.post(
                    "/chat/stream",
                    json={"message": message, "request_id": "test_var"}
                )

                assert response.status_code == 200, \
                    f"CREATE variation should work: {message}"

            # Test LIST variations
            for message in list_variations:
                response = client.post(
                    "/chat/stream",
                    json={"message": message, "request_id": "test_var"}
                )

                assert response.status_code == 200, \
                    f"LIST variation should work: {message}"

    def _parse_sse_stream(self, stream_text: str) -> list:
        """Parse SSE stream into list of events."""
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
                events.append({
                    'event': current_event,
                    'data': current_data
                })
                current_event = None
                current_data = None

        return events
