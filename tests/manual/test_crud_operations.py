"""
T027: Manual testing script for all 5 CRUD operations via agent

This script tests agent tool execution with create, list, update, search, and delete operations
in the development environment. Run this after starting the development server.

Usage:
    # Start development server first:
    uv run uvicorn src.main:app --reload

    # Then run this test script:
    uv run python tests/manual/test_crud_operations.py

Expected Results:
- All 5 CRUD operations execute successfully
- Agent correctly extracts intent and parameters from natural language
- SSE events stream properly (THINKING, TOOL_CALL, RESPONSE_DELTA, DONE)
- Database operations persist correctly
"""

import requests
import json
import time
from typing import List, Dict

# Development server URL
API_BASE_URL = "http://localhost:8000"
CHAT_STREAM_ENDPOINT = f"{API_BASE_URL}/chat/stream"


def parse_sse_stream(response_text: str) -> List[Dict]:
    """Parse SSE stream into list of events."""
    events = []
    lines = response_text.strip().split('\n')

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


def test_operation(operation_name: str, message: str, expected_tool: str) -> bool:
    """
    Test a single CRUD operation.

    Args:
        operation_name: Human-readable operation name (e.g., "CREATE TODO")
        message: Natural language message to send to agent
        expected_tool: Expected MCP tool name (e.g., "create_todo")

    Returns:
        True if test passed, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Testing: {operation_name}")
    print(f"Message: {message}")
    print(f"Expected Tool: {expected_tool}")
    print(f"{'='*80}\n")

    try:
        # Send request
        response = requests.post(
            CHAT_STREAM_ENDPOINT,
            json={"message": message, "request_id": f"test_{operation_name}"},
            stream=True,
            timeout=30
        )

        # Check HTTP status
        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

        # Parse SSE stream
        events = parse_sse_stream(response.text)

        # Verify events
        print(f"Received {len(events)} events:")

        event_types = [e['event'] for e in events]
        print(f"Event types: {' → '.join(event_types)}")

        # Check for expected event types
        has_thinking = 'thinking' in event_types
        has_tool_call = 'tool_call' in event_types
        has_response = 'response_delta' in event_types or 'done' in event_types
        has_done = 'done' in event_types

        print(f"\nEvent Validation:")
        print(f"  THINKING present: {'✓' if has_thinking else '✗'}")
        print(f"  TOOL_CALL present: {'✓' if has_tool_call else '✗'}")
        print(f"  RESPONSE present: {'✓' if has_response else '✗'}")
        print(f"  DONE present: {'✓' if has_done else '✗'}")

        # Check if expected tool was called
        tool_call_events = [e for e in events if e['event'] == 'tool_call']
        tool_called = False

        if tool_call_events:
            for tool_event in tool_call_events:
                tool_data = tool_event['data']
                tool_name = tool_data.get('tool_name', '')

                print(f"\nTool Call:")
                print(f"  Tool: {tool_name}")
                print(f"  Arguments: {json.dumps(tool_data.get('arguments', {}), indent=4)}")
                print(f"  Status: {tool_data.get('status', 'unknown')}")

                if expected_tool in tool_name.lower():
                    tool_called = True

        # Check final result
        done_events = [e for e in events if e['event'] == 'done']
        success = False

        if done_events:
            done_data = done_events[0]['data']
            success = done_data.get('success', False)

            print(f"\nFinal Result:")
            print(f"  Success: {success}")
            print(f"  Tools Called: {done_data.get('tools_called', [])}")
            print(f"  Output: {done_data.get('final_output', '')[:100]}...")

        # Overall test result
        test_passed = (
            has_done and
            tool_called and
            success
        )

        if test_passed:
            print(f"\n✅ {operation_name} TEST PASSED")
        else:
            print(f"\n❌ {operation_name} TEST FAILED")
            if not has_done:
                print("   - Missing DONE event")
            if not tool_called:
                print(f"   - Expected tool '{expected_tool}' was not called")
            if not success:
                print("   - Operation did not succeed")

        return test_passed

    except requests.exceptions.ConnectionError:
        print(f"❌ FAILED: Cannot connect to {API_BASE_URL}")
        print("   Make sure the development server is running:")
        print("   uv run uvicorn src.main:app --reload")
        return False

    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False


def main():
    """
    Main test runner for all 5 CRUD operations.
    """
    print("\n" + "="*80)
    print(" T027: Testing All 5 CRUD Operations via Agent".center(80))
    print("="*80)

    # Check if server is running
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"\n✓ Server is running (Health Status: {health_response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Server is not running at {API_BASE_URL}")
        print("\nPlease start the development server first:")
        print("  uv run uvicorn src.main:app --reload")
        print("\nThen run this test script again.")
        return

    # Define test cases for all 5 CRUD operations
    tests = [
        # Operation 1: CREATE
        {
            "name": "CREATE TODO",
            "message": "Create a task to buy groceries for dinner",
            "expected_tool": "create_todo"
        },

        # Operation 2: LIST
        {
            "name": "LIST TODOS",
            "message": "What are my active tasks?",
            "expected_tool": "list_todos"
        },

        # Operation 3: UPDATE
        {
            "name": "UPDATE TODO",
            "message": "Mark the grocery shopping task as completed",
            "expected_tool": "update_todo"
        },

        # Operation 4: SEARCH
        {
            "name": "SEARCH TODOS",
            "message": "Find todos about groceries",
            "expected_tool": "search_todos"
        },

        # Operation 5: DELETE
        {
            "name": "DELETE TODO",
            "message": "Delete the completed grocery task",
            "expected_tool": "delete_todo"
        }
    ]

    # Run all tests
    results = []

    for test in tests:
        result = test_operation(
            operation_name=test["name"],
            message=test["message"],
            expected_tool=test["expected_tool"]
        )
        results.append((test["name"], result))

        # Small delay between tests
        time.sleep(1)

    # Print summary
    print("\n" + "="*80)
    print(" TEST SUMMARY".center(80))
    print("="*80)

    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for operation, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{operation:20s} : {status}")

    print(f"\n{'='*80}")
    print(f"Results: {passed_count}/{total_count} tests passed")
    print(f"{'='*80}\n")

    if passed_count == total_count:
        print("🎉 All CRUD operations working correctly!")
        print("\nT027 verification complete: Agent successfully executes all 5 CRUD operations.")
    else:
        print("⚠️ Some tests failed. Please check the output above for details.")
        print("\nRecommendations:")
        print("  1. Verify MCP server is connected (check /health endpoint)")
        print("  2. Check agent configuration in src/agents/todo_agent.py")
        print("  3. Verify all 5 MCP tools are registered")
        print("  4. Review agent logs for errors")


if __name__ == "__main__":
    main()
