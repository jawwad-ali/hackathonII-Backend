import json

from agents.stream_events import RawResponsesStreamEvent, RunItemStreamEvent
from agents.items import ToolCallItem, ToolCallOutputItem
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall

from src.streaming.chatkit import StreamBuilder, map_agent_event_to_chatkit


class _DummyAgent:
    pass


def _parse_sse_data(sse: str) -> dict:
    lines = [line.strip() for line in sse.strip().splitlines() if line.strip()]
    assert lines[0].startswith("event:")
    assert lines[1].startswith("data:")
    payload = lines[1].split("data:", 1)[1].strip()
    return json.loads(payload)


def test_sse_event_type_is_value_not_enum_name():
    builder = StreamBuilder()
    sse = builder.add_thinking("hello")
    assert "event: thinking" in sse
    assert "EventType." not in sse


def test_maps_raw_text_delta_to_response_delta():
    builder = StreamBuilder()
    raw = ResponseTextDeltaEvent(
        content_index=0,
        delta="Hello",
        item_id="item_1",
        logprobs=[],
        output_index=0,
        sequence_number=0,
        type="response.output_text.delta",
    )
    event = RawResponsesStreamEvent(data=raw)

    sse = map_agent_event_to_chatkit(event, builder)
    assert sse is not None
    assert "event: response_delta" in sse
    assert builder.accumulated_text == "Hello"

    data = _parse_sse_data(sse)
    assert data["delta"] == "Hello"
    assert data["accumulated"] == "Hello"


def test_maps_tool_call_and_correlates_tool_output():
    builder = StreamBuilder()
    dummy_agent = _DummyAgent()

    tool_call = ResponseFunctionToolCall(
        arguments=json.dumps({"title": "Buy eggs"}),
        call_id="call_1",
        name="create_todo",
        type="function_call",
    )
    tool_call_item = ToolCallItem(agent=dummy_agent, raw_item=tool_call)
    tool_called_event = RunItemStreamEvent(name="tool_called", item=tool_call_item)

    sse_called = map_agent_event_to_chatkit(tool_called_event, builder)
    assert sse_called is not None
    assert "event: tool_call" in sse_called
    assert "create_todo" in sse_called

    data_called = _parse_sse_data(sse_called)
    assert data_called["tool_name"] == "create_todo"
    assert data_called["status"] == "in_progress"
    assert data_called["arguments"] == {"title": "Buy eggs"}

    # Now send a correlated tool output event by call_id
    tool_output_item = ToolCallOutputItem(
        agent=dummy_agent,
        raw_item={"call_id": "call_1", "output": "ok", "type": "function_call_output"},
        output="ok",
    )
    tool_output_event = RunItemStreamEvent(name="tool_output", item=tool_output_item)

    sse_output = map_agent_event_to_chatkit(tool_output_event, builder)
    assert sse_output is not None
    assert "event: tool_call" in sse_output

    data_output = _parse_sse_data(sse_output)
    assert data_output["tool_name"] == "create_todo"
    assert data_output["status"] == "completed"
