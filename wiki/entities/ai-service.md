---
title: AIService — Multi-turn Tool Loop
type: entity
tags: [ai, litellm, tools, agent]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/services/ai.py, backend/services/tools.py]
---

`AIService` in `backend/services/ai.py:19` wraps LiteLLM's synchronous `completion()` in a bounded multi-turn tool-calling loop. One instance (`ai_service`, line 116) is imported by the chat route.

## Loop invariants

- The loop runs at most `max_tool_turns + 1` iterations. The `+1` exists so the model gets one final turn to produce content *after* its last tool call.
- On hitting the cap, the service returns a fixed string asking the user to break the request down.
- Every model turn with `tool_calls` appends the assistant message (as a plain dict) plus one `role: tool` message per call to the running `messages` list before re-calling `completion()`.
- The original `messages` argument is defensively copied (`backend/services/ai.py:45`) — callers can reuse their list.

## Configuration precedence

`max_tool_turns` resolution (high→low):
1. Explicit constructor kwarg.
2. `AI_MAX_TOOL_TURNS` env var (parsed by `_parse_env_cap`; malformed values log a warning and fall back to the default).
3. `DEFAULT_MAX_TOOL_TURNS = 6`.

Model selection: `DEFAULT_AI_MODEL` env var overrides the constructor `model` kwarg. If neither is set, the hardcoded default is `"gpt-4o"`.

## Error handling

- **Tool JSON argument parse errors** become `"Error: could not parse tool arguments JSON: ..."` and are fed back to the model as the tool result. The loop continues.
- **Tool exceptions** are caught per-call; the traceback is logged, the model sees `"Error executing <tool>: <message>"`.
- **Top-level exceptions** (e.g. LiteLLM rate limit, auth failure) return a user-facing string naming the model; details go to the logs only.

## Related

- [[entities/http-api]] — the `/api/chat` route drives this service.
- [[concepts/tool-calling-flow]] — what tools exist, how they chain.
- [[concepts/configuration]] — where `AI_MAX_TOOL_TURNS` and `DEFAULT_AI_MODEL` come from.
