"""LLM-driven pinout extraction from a datasheet URL.

Flow:
    datasheet_url -> fetch PDF -> extract text -> LLM structured JSON -> PinSpec[]

The LLM call is a **second**, dedicated completion so the primary agent context
doesn't get flooded with tens of thousands of tokens of datasheet noise.
"""
from __future__ import annotations

import json
import logging
import os

from litellm import completion

from backend.services.datasheet import extract_datasheet_text
from backend.services.procedural_symbol import VALID_PIN_TYPES, PinSpec

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS = 60_000

_SYSTEM_PROMPT = (
    "You extract electronic component pinouts from datasheet text.\n"
    "Return ONLY a JSON array of objects with keys:\n"
    '  "number" (string): the pin number as printed on the package\n'
    '  "name"   (string): the pin name/label\n'
    '  "type"   (string): one of "input", "output", "bidirectional", '
    '"tri_state", "passive", "power_in", "power_out", '
    '"open_collector", "open_emitter", "unspecified", "no_connect"\n'
    "Return an empty array [] if no pinout is discoverable.\n"
    "Do not include any prose, explanation, or markdown fences — just the JSON."
)


class PinoutExtractionError(Exception):
    """Raised when pin extraction fails after the datasheet was successfully fetched."""


def _parse_pin_json(raw: str) -> list[PinSpec]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Strip an opening fence like ``` or ```json, plus the matching close.
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1 :] if first_newline != -1 else ""
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise PinoutExtractionError(f"LLM did not return valid JSON: {e}") from e

    if not isinstance(data, list):
        raise PinoutExtractionError("LLM response was not a JSON array.")

    pins: list[PinSpec] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        number = str(entry.get("number", "")).strip()
        name = str(entry.get("name", "")).strip()
        type_ = str(entry.get("type", "")).strip().lower()
        if not number or not name:
            continue
        if type_ not in VALID_PIN_TYPES:
            logger.info("Dropping pin %s (%s): unknown type %r", number, name, type_)
            continue
        pins.append(PinSpec(number=number, name=name, type=type_))

    if not pins:
        raise PinoutExtractionError("No valid pins extracted from datasheet.")
    return pins


async def extract_pinout(
    datasheet_url: str,
    mpn: str,
    *,
    model: str | None = None,
) -> list[PinSpec]:
    text = await extract_datasheet_text(datasheet_url)
    if len(text) > _MAX_TEXT_CHARS:
        logger.info(
            "Truncating datasheet text from %d to %d chars for %s",
            len(text), _MAX_TEXT_CHARS, mpn,
        )
        text = text[:_MAX_TEXT_CHARS]

    chosen_model = model or os.getenv("DEFAULT_AI_MODEL", "gpt-4o")
    response = completion(
        model=chosen_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Component MPN: {mpn}\n\nDatasheet text:\n{text}",
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return _parse_pin_json(content)
