"""Build a KiCad 9 `(symbol ...)` S-expression from a pin list.

Used as a fallback when a library symbol is not available for a requested MPN.
Layout: pins distributed on left/right edges, one body rectangle sized to fit.
"""
from __future__ import annotations

from dataclasses import dataclass

VALID_PIN_TYPES = {
    "input", "output", "bidirectional", "tri_state", "passive",
    "power_in", "power_out", "open_collector", "open_emitter",
    "unspecified", "no_connect",
}


@dataclass(frozen=True)
class PinSpec:
    number: str
    name: str
    type: str  # One of VALID_PIN_TYPES

    def __post_init__(self) -> None:
        if self.type not in VALID_PIN_TYPES:
            raise ValueError(f"Invalid pin type: {self.type}")


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\x00", "")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def build_procedural_symbol(*, name: str, pins: list[PinSpec]) -> str:
    """Return the `(symbol ...)` S-expression for a rectangular symbol with named pins."""
    if not pins:
        raise ValueError("build_procedural_symbol requires at least one pin")

    left = pins[: (len(pins) + 1) // 2]
    right = pins[(len(pins) + 1) // 2 :]

    height = max(len(left), len(right), 2) * 2.54
    half_h = height / 2 + 2.54
    width = 5.08 * 2  # total width of the body; grows if needed
    half_w = width / 2

    pin_lines: list[str] = []
    for i, p in enumerate(left):
        y = half_h - 2.54 - i * 2.54
        pin_lines.append(
            f'    (pin {p.type} line (at {-half_w - 2.54} {y} 0) (length 2.54)\n'
            f'      (name "{_escape(p.name)}" (effects (font (size 1.27 1.27))))\n'
            f'      (number "{_escape(p.number)}" (effects (font (size 1.27 1.27)))))\n'
        )
    for i, p in enumerate(right):
        y = half_h - 2.54 - i * 2.54
        pin_lines.append(
            f'    (pin {p.type} line (at {half_w + 2.54} {y} 180) (length 2.54)\n'
            f'      (name "{_escape(p.name)}" (effects (font (size 1.27 1.27))))\n'
            f'      (number "{_escape(p.number)}" (effects (font (size 1.27 1.27)))))\n'
        )

    safe_name = _escape(name)
    return (
        f'(symbol "{safe_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n'
        f'  (property "Reference" "U" (at 0 {half_h + 2.54} 0)(effects (font (size 1.27 1.27))))\n'
        f'  (property "Value" "{safe_name}" (at 0 {half_h} 0)(effects (font (size 1.27 1.27))))\n'
        f'  (property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27)) hide))\n'
        f'  (symbol "{safe_name}_0_1"\n'
        f'    (rectangle (start {-half_w} {half_h - 2.54}) (end {half_w} {-half_h + 2.54})\n'
        f'      (stroke (width 0.254) (type default))(fill (type background)))\n'
        f'  )\n'
        f'  (symbol "{safe_name}_1_1"\n'
        + "".join(pin_lines)
        + "  )\n)\n"
    )
