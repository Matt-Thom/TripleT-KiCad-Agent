import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.ai import AIService


def _make_tool_call(call_id, fn_name, args_json):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=fn_name, arguments=args_json),
    )


def _make_completion(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls or None)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_get_response_executes_chained_tool_calls():
    """The loop must execute tool calls, feed results back, and continue until a text reply."""
    svc = AIService(model="test-model")

    responses = [
        _make_completion(tool_calls=[_make_tool_call("c1", "search_lcsc", '{"query": "STM32"}')]),
        _make_completion(tool_calls=[_make_tool_call(
            "c2", "generate_schematic", '{"mpn": "STM32F103", "supplier_id": "C8734"}'
        )]),
        _make_completion(content="Done. [Download STM32F103 Schematic](/api/download/STM32F103_C8734.kicad_sch)"),
    ]
    call_count = {"n": 0}

    async def fake_completion(**kwargs):
        i = call_count["n"]
        call_count["n"] += 1
        return responses[i]

    async def fake_execute_tool(name, args, project_id=None):
        if name == "search_lcsc":
            return '[{"mpn": "STM32F103", "supplier_part_number": "C8734"}]'
        if name == "generate_schematic":
            return "Schematic generated. [Download]"
        return "Error: unknown tool"

    with patch("backend.services.ai.acompletion", side_effect=fake_completion):
        with patch("backend.services.ai.execute_tool", side_effect=fake_execute_tool):
            result = asyncio.run(svc.get_response([{"role": "user", "content": "Make an STM32 sch"}]))

    assert "Download" in result
    assert call_count["n"] == 3  # Two tool rounds + final text


def test_get_response_respects_max_turns():
    """Loop must break after MAX_TURNS even if the model keeps requesting tools."""
    svc = AIService(model="test-model", max_tool_turns=2)

    call_count = {"n": 0}

    async def always_tool_call(**kwargs):
        call_count["n"] += 1
        return _make_completion(tool_calls=[_make_tool_call("c", "search_lcsc", '{"query": "X"}')])

    async def fake_execute_tool(name, args, project_id=None):
        return "results..."

    with patch("backend.services.ai.acompletion", side_effect=always_tool_call):
        with patch("backend.services.ai.execute_tool", side_effect=fake_execute_tool):
            result = asyncio.run(svc.get_response([{"role": "user", "content": "loop forever"}]))

    # Should surface a graceful cap message, not an exception
    assert "maximum" in result.lower() or "limit" in result.lower()
    # range(max_tool_turns + 1) == range(3) → exactly 3 completion() invocations
    assert call_count["n"] == 3


def test_get_response_recovers_from_tool_error():
    """A raising tool should be reported back to the model as a tool result, not propagated."""
    svc = AIService(model="test-model")

    responses = [
        _make_completion(tool_calls=[_make_tool_call("c1", "search_lcsc", '{"query": "X"}')]),
        _make_completion(content="I saw the error; here is what to try instead: ..."),
    ]
    call_count = {"n": 0}

    async def fake_completion(**kwargs):
        i = call_count["n"]
        call_count["n"] += 1
        # Ensure the tool-result message contains the error text
        if i == 1:
            tool_msgs = [m for m in kwargs["messages"] if m.get("role") == "tool"]
            assert tool_msgs and "boom" in tool_msgs[-1]["content"]
        return responses[i]

    async def raising_tool(name, args, project_id=None):
        raise RuntimeError("boom")

    with patch("backend.services.ai.acompletion", side_effect=fake_completion):
        with patch("backend.services.ai.execute_tool", side_effect=raising_tool):
            result = asyncio.run(svc.get_response([{"role": "user", "content": "try it"}]))

    assert "try instead" in result


def test_get_response_no_tool_calls_returns_content():
    svc = AIService(model="test-model")
    with patch(
        "backend.services.ai.acompletion",
        AsyncMock(return_value=_make_completion(content="pure text answer")),
    ):
        result = asyncio.run(svc.get_response([{"role": "user", "content": "hi"}]))
    assert result == "pure text answer"
