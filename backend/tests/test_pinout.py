"""Tests for backend.services.pinout — LLM-driven pinout extraction."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.services.procedural_symbol import PinSpec


def test_parse_pin_json_returns_pinspecs():
    from backend.services.pinout import _parse_pin_json

    raw = (
        '[{"number":"1","name":"VCC","type":"power_in"},'
        '{"number":"2","name":"GND","type":"power_in"}]'
    )
    pins = _parse_pin_json(raw)

    assert pins == [
        PinSpec(number="1", name="VCC", type="power_in"),
        PinSpec(number="2", name="GND", type="power_in"),
    ]


def test_parse_pin_json_strips_markdown_fences():
    from backend.services.pinout import _parse_pin_json

    raw = '```json\n[{"number":"1","name":"VCC","type":"power_in"}]\n```'
    pins = _parse_pin_json(raw)

    assert pins[0].name == "VCC"


def test_parse_pin_json_drops_pins_with_unknown_types():
    from backend.services.pinout import _parse_pin_json

    raw = (
        '[{"number":"1","name":"VCC","type":"power_in"},'
        '{"number":"2","name":"BAD","type":"nonsense"}]'
    )
    pins = _parse_pin_json(raw)

    assert len(pins) == 1
    assert pins[0].name == "VCC"


def test_parse_pin_json_raises_when_all_pins_invalid():
    from backend.services.pinout import PinoutExtractionError, _parse_pin_json

    raw = '[{"number":"1","name":"X","type":"weird"}]'
    with pytest.raises(PinoutExtractionError):
        _parse_pin_json(raw)


def test_parse_pin_json_raises_on_non_array():
    from backend.services.pinout import PinoutExtractionError, _parse_pin_json

    raw = '{"pins": []}'
    with pytest.raises(PinoutExtractionError):
        _parse_pin_json(raw)


def test_parse_pin_json_raises_on_invalid_json():
    from backend.services.pinout import PinoutExtractionError, _parse_pin_json

    with pytest.raises(PinoutExtractionError):
        _parse_pin_json("not json at all")


@pytest.mark.asyncio
async def test_extract_pinout_end_to_end(monkeypatch):
    from backend.services import pinout as pin_mod

    async def fake_extract_text(url: str) -> str:
        assert url == "https://example.com/ds.pdf"
        return "Pin 1 VCC Power supply\nPin 2 GND Ground"

    monkeypatch.setattr(pin_mod, "extract_datasheet_text", fake_extract_text)

    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(
            message=MagicMock(
                content='[{"number":"1","name":"VCC","type":"power_in"},'
                '{"number":"2","name":"GND","type":"power_in"}]'
            )
        )
    ]
    monkeypatch.setattr(pin_mod, "completion", lambda **kwargs: fake_response)

    pins = await pin_mod.extract_pinout("https://example.com/ds.pdf", "STM32F103")

    assert pins == [
        PinSpec(number="1", name="VCC", type="power_in"),
        PinSpec(number="2", name="GND", type="power_in"),
    ]


@pytest.mark.asyncio
async def test_extract_pinout_truncates_large_pdf_text(monkeypatch):
    from backend.services import pinout as pin_mod

    huge = "X" * 500_000

    async def fake_extract_text(url: str) -> str:
        return huge

    monkeypatch.setattr(pin_mod, "extract_datasheet_text", fake_extract_text)

    captured_messages: dict = {}

    def fake_completion(**kwargs):
        captured_messages["messages"] = kwargs["messages"]
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(
                    content='[{"number":"1","name":"VCC","type":"power_in"}]'
                )
            )
        ]
        return response

    monkeypatch.setattr(pin_mod, "completion", fake_completion)

    await pin_mod.extract_pinout("https://example.com/big.pdf", "BIG")

    user_msg = captured_messages["messages"][-1]["content"]
    assert len(user_msg) < len(huge)


def test_extract_pinout_tool_is_registered():
    from backend.services.tools import tools

    names = [t["function"]["name"] for t in tools]
    assert "extract_pinout" in names

    spec = next(t for t in tools if t["function"]["name"] == "extract_pinout")
    params = spec["function"]["parameters"]
    assert "datasheet_url" in params["properties"]
    assert "mpn" in params["properties"]
    assert set(params["required"]) == {"datasheet_url", "mpn"}


@pytest.mark.asyncio
async def test_execute_tool_extract_pinout_returns_serialized_pins(monkeypatch):
    from backend.services import tools as tools_mod

    async def fake_extract_pinout(datasheet_url: str, mpn: str):
        assert datasheet_url == "https://example.com/ds.pdf"
        assert mpn == "STM32"
        return [
            PinSpec(number="1", name="VCC", type="power_in"),
            PinSpec(number="2", name="GND", type="power_in"),
        ]

    monkeypatch.setattr(tools_mod, "extract_pinout", fake_extract_pinout)

    result = await tools_mod.execute_tool(
        "extract_pinout",
        {"datasheet_url": "https://example.com/ds.pdf", "mpn": "STM32"},
    )

    assert "VCC" in result
    assert "GND" in result
    assert '"1"' in result or "'1'" in result


@pytest.mark.asyncio
async def test_execute_tool_extract_pinout_reports_errors(monkeypatch):
    from backend.services import tools as tools_mod
    from backend.services.datasheet import DatasheetError

    async def fake_extract_pinout(datasheet_url: str, mpn: str):
        raise DatasheetError("404 Not Found")

    monkeypatch.setattr(tools_mod, "extract_pinout", fake_extract_pinout)

    result = await tools_mod.execute_tool(
        "extract_pinout",
        {"datasheet_url": "https://example.com/missing.pdf", "mpn": "X"},
    )

    assert "Error" in result or "error" in result
    assert "404" in result


def test_generate_schematic_tool_accepts_optional_pins():
    from backend.services.tools import tools

    spec = next(t for t in tools if t["function"]["name"] == "generate_schematic")
    props = spec["function"]["parameters"]["properties"]
    assert "pins" in props
    assert props["pins"]["type"] == "array"
    # pins should remain optional
    assert "pins" not in spec["function"]["parameters"].get("required", [])


@pytest.mark.asyncio
async def test_execute_tool_generate_schematic_passes_pins(monkeypatch):
    from backend.services import tools as tools_mod

    captured: dict = {}

    def fake_generate(mpn, supplier_id, *, description="", pins=None):
        captured["mpn"] = mpn
        captured["pins"] = pins
        return "/tmp/generated_schematics/X_C1.kicad_sch"

    monkeypatch.setattr(
        tools_mod.schematic_service,
        "generate_single_component_sch",
        fake_generate,
    )

    await tools_mod.execute_tool(
        "generate_schematic",
        {
            "mpn": "STM32",
            "supplier_id": "C1",
            "pins": [
                {"number": "1", "name": "VCC", "type": "power_in"},
                {"number": "2", "name": "GND", "type": "power_in"},
            ],
        },
    )

    assert captured["mpn"] == "STM32"
    assert captured["pins"] == [
        PinSpec(number="1", name="VCC", type="power_in"),
        PinSpec(number="2", name="GND", type="power_in"),
    ]
