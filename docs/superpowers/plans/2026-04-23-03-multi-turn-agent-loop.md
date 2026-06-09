# Multi-Turn Agent Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `AIService.get_response`'s single-round tool-call loop with a bounded multi-turn loop so the agent can chain `lookup_pattern → apply_pattern`, `search_lcsc → generate_schematic`, or any sequence up to a configurable turn cap.

**Architecture:** `AIService.get_response` runs `while response.tool_calls and turns < MAX_TURNS: execute tools, append results, re-invoke completion`. Per-turn structured logging via `logging`. Errors inside tool execution are caught and fed back to the model as tool results so the model can recover (not raised to the client).

**Tech Stack:** No new deps. Python stdlib `logging`, `litellm`.

**Prerequisite:** Plans 01 and 02 landed (more tools to chain = higher value from loop).

**Branch:** `feat/multi-turn-agent-loop` off `dev`.

---

## File Structure

- Modify: `backend/services/ai.py` — rewrite `get_response`.
- Create: `backend/tests/test_ai_service.py`
- Modify: `.env.example` — document `AI_MAX_TOOL_TURNS`.

---

## Task 1: Failing test for multi-turn behaviour

**Files:**
- Create: `backend/tests/test_ai_service.py`

- [ ] **Step 1: Write failing tests**

```python
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def test_get_response_executes_chained_tool_calls(monkeypatch):
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

    def fake_completion(**kwargs):
        i = call_count["n"]
        call_count["n"] += 1
        return responses[i]

    async def fake_execute_tool(name, args):
        if name == "search_lcsc":
            return '[{"mpn": "STM32F103", "supplier_part_number": "C8734"}]'
        if name == "generate_schematic":
            return "Schematic generated. [Download]"
        return "Error: unknown tool"

    with patch("backend.services.ai.completion", side_effect=fake_completion):
        with patch("backend.services.ai.execute_tool", side_effect=fake_execute_tool):
            result = asyncio.run(svc.get_response([{"role": "user", "content": "Make an STM32 sch"}]))

    assert "Download" in result
    assert call_count["n"] == 3  # Two tool rounds + final text


def test_get_response_respects_max_turns(monkeypatch):
    """Loop must break after MAX_TURNS even if the model keeps requesting tools."""
    svc = AIService(model="test-model", max_tool_turns=2)

    def always_tool_call(**kwargs):
        return _make_completion(tool_calls=[_make_tool_call("c", "search_lcsc", '{"query": "X"}')])

    async def fake_execute_tool(name, args):
        return "results..."

    with patch("backend.services.ai.completion", side_effect=always_tool_call):
        with patch("backend.services.ai.execute_tool", side_effect=fake_execute_tool):
            result = asyncio.run(svc.get_response([{"role": "user", "content": "loop forever"}]))

    # Should surface a graceful cap message, not an exception
    assert "maximum" in result.lower() or "limit" in result.lower()


def test_get_response_recovers_from_tool_error(monkeypatch):
    """A raising tool should be reported back to the model as a tool result, not propagated."""
    svc = AIService(model="test-model")

    responses = [
        _make_completion(tool_calls=[_make_tool_call("c1", "search_lcsc", '{"query": "X"}')]),
        _make_completion(content="I saw the error; here is what to try instead: ..."),
    ]
    call_count = {"n": 0}

    def fake_completion(**kwargs):
        i = call_count["n"]
        call_count["n"] += 1
        # Ensure the tool-result message contains the error text
        if i == 1:
            tool_msgs = [m for m in kwargs["messages"] if m.get("role") == "tool"]
            assert tool_msgs and "boom" in tool_msgs[-1]["content"]
        return responses[i]

    async def raising_tool(name, args):
        raise RuntimeError("boom")

    with patch("backend.services.ai.completion", side_effect=fake_completion):
        with patch("backend.services.ai.execute_tool", side_effect=raising_tool):
            result = asyncio.run(svc.get_response([{"role": "user", "content": "try it"}]))

    assert "try instead" in result


def test_get_response_no_tool_calls_returns_content():
    svc = AIService(model="test-model")
    with patch(
        "backend.services.ai.completion",
        return_value=_make_completion(content="pure text answer"),
    ):
        result = asyncio.run(svc.get_response([{"role": "user", "content": "hi"}]))
    assert result == "pure text answer"
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_ai_service.py -v
```

Expected: `test_get_response_respects_max_turns` and `test_get_response_executes_chained_tool_calls` both fail — the current single-round loop only makes 2 completion calls and doesn't accept `max_tool_turns` as a constructor kwarg.

- [ ] **Step 3: Commit**

```bash
git checkout -b feat/multi-turn-agent-loop
git add backend/tests/test_ai_service.py
git commit -m "test: failing tests for multi-turn AI loop + max-turns + error recovery"
```

---

## Task 2: Rewrite `AIService.get_response`

**Files:**
- Modify: `backend/services/ai.py`

- [ ] **Step 1: Replace the file**

```python
"""AI service with a bounded multi-turn tool-calling loop."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from litellm import completion

from backend.services.tools import tools, execute_tool

load_dotenv()

logger = logging.getLogger(__name__)


class AIService:
    DEFAULT_MAX_TOOL_TURNS = 6

    def __init__(self, model: str = "gpt-4o", max_tool_turns: int | None = None) -> None:
        self.model = os.getenv("DEFAULT_AI_MODEL", model)
        env_cap = os.getenv("AI_MAX_TOOL_TURNS")
        self.max_tool_turns = (
            max_tool_turns
            if max_tool_turns is not None
            else int(env_cap) if env_cap else self.DEFAULT_MAX_TOOL_TURNS
        )

    async def get_response(self, messages: list[dict[str, Any]]) -> str:
        messages = list(messages)  # Defensive copy — we mutate inside the loop.
        try:
            for turn in range(self.max_tool_turns + 1):
                response = completion(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                message = response.choices[0].message
                tool_calls = getattr(message, "tool_calls", None)

                if not tool_calls:
                    return message.content or ""

                if turn == self.max_tool_turns:
                    logger.warning(
                        "AI loop hit max_tool_turns=%d without a final answer", self.max_tool_turns
                    )
                    return (
                        "I reached the maximum number of tool-call turns without producing a final "
                        "answer. Try breaking your request into smaller steps."
                    )

                messages.append(message)

                for tool_call in tool_calls:
                    fn_name = tool_call.function.name
                    raw_args = tool_call.function.arguments
                    try:
                        fn_args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError as e:
                        result = f"Error: could not parse tool arguments JSON: {e}"
                        logger.warning("Invalid tool args for %s: %s", fn_name, raw_args)
                    else:
                        logger.info("AI tool call: %s(%s)", fn_name, fn_args)
                        try:
                            result = await execute_tool(fn_name, fn_args)
                        except Exception as e:
                            logger.exception("Tool %s raised", fn_name)
                            result = f"Error executing {fn_name}: {e}"

                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": fn_name,
                            "content": str(result),
                        }
                    )
            # Unreachable — the for-loop returns inside.
            return ""
        except Exception as e:
            logger.exception("AI service top-level error")
            return (
                "Error: I'm having trouble thinking right now. "
                f"Model: {self.model}. Details were logged server-side."
            )


ai_service = AIService()
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_ai_service.py -v
```

Expected: all 4 pass.

- [ ] **Step 3: Run the full backend suite**

```bash
uv run pytest backend -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/services/ai.py
git commit -m "feat(agent): bounded multi-turn tool-calling loop with error recovery"
```

---

## Task 3: Document the env knob

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Append**

```
# Optional: maximum number of tool-calling turns per chat response. Default 6.
AI_MAX_TOOL_TURNS=6
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: document AI_MAX_TOOL_TURNS"
```

---

## Task 4: Manual verification + PR

- [ ] **Step 1: Manual check (with plans 01 and 02 merged)**

Start the backend with real API keys and ask:

> "Design a 3.3V rail from USB-C input with an LDO and decoupling caps."

Expected: the agent calls `lookup_pattern` (finds `usb_c_input` + `ldo_regulator`), then `apply_pattern` twice (or a chained sequence). Watch the server log for the per-turn `AI tool call: ...` lines.

- [ ] **Step 2: Open PR**

```bash
git push -u origin feat/multi-turn-agent-loop
gh pr create --base dev --title "feat(agent): bounded multi-turn tool-calling loop" --body "$(cat <<'EOF'
## Summary
- Replaces single-round loop with a while-loop capped at AI_MAX_TOOL_TURNS (default 6).
- Tool exceptions are reported back to the model as tool results rather than surfaced as errors.
- Per-turn structured logging at INFO.

## Test plan
- [x] Unit tests for chain, cap, error-recovery, and no-tool-call paths.
- [ ] Manual: "Design a 3.3V rail from USB-C with an LDO" — agent chains lookup_pattern + apply_pattern at least twice.
EOF
)"
```
