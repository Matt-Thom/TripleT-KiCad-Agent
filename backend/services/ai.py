"""AI service with a bounded multi-turn tool-calling loop."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from litellm import acompletion

from backend.services.tools import tools, execute_tool

load_dotenv()

logger = logging.getLogger(__name__)


class AIService:
    # A full design pass (plan blocks, search N parts, extract N pinouts,
    # build the IR, run ERC, compile) easily needs 15+ tool turns.
    DEFAULT_MAX_TOOL_TURNS = 24

    def __init__(self, model: str = "gpt-4o", max_tool_turns: int | None = None) -> None:
        self.model = os.getenv("DEFAULT_AI_MODEL", model)
        env_cap = os.getenv("AI_MAX_TOOL_TURNS")
        self.max_tool_turns = (
            max_tool_turns
            if max_tool_turns is not None
            else self._parse_env_cap(env_cap)
        )

    @classmethod
    def _parse_env_cap(cls, env_cap: str | None) -> int:
        if not env_cap:
            return cls.DEFAULT_MAX_TOOL_TURNS
        try:
            return int(env_cap.strip())
        except ValueError:
            logger.warning(
                "Invalid AI_MAX_TOOL_TURNS=%r; falling back to default %d",
                env_cap, cls.DEFAULT_MAX_TOOL_TURNS,
            )
            return cls.DEFAULT_MAX_TOOL_TURNS

    async def get_response(
        self,
        messages: list[dict[str, Any]],
        project_id: int | None = None,
    ) -> str:
        messages = list(messages)  # Defensive copy — we mutate inside the loop.
        try:
            for turn in range(self.max_tool_turns + 1):
                response = await acompletion(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                message = response.choices[0].message
                tool_calls = getattr(message, "tool_calls", None)

                if not tool_calls:
                    if not message.content:
                        logger.warning(
                            "Model returned neither content nor tool_calls; returning empty reply"
                        )
                    return message.content or ""

                if turn == self.max_tool_turns:
                    logger.warning(
                        "AI loop hit max_tool_turns=%d without a final answer", self.max_tool_turns
                    )
                    return (
                        "I reached the maximum number of tool-call turns without producing a final "
                        "answer. Try breaking your request into smaller steps."
                    )

                # Append as a dict so downstream message-list consumers can use .get().
                # Both litellm Message objects and SimpleNamespace test mocks have __dict__,
                # so we can always rebuild a clean dict here.
                messages.append({
                    "role": getattr(message, "role", "assistant"),
                    "content": getattr(message, "content", None),
                    "tool_calls": tool_calls,
                })

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
                            result = await execute_tool(fn_name, fn_args, project_id=project_id)
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
