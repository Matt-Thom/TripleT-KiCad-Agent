"""Map physical package names (as reported by LCSC/JLC) to KiCad footprint IDs.

The mapping is intentionally conservative: it only returns a footprint when the
package string clearly identifies a standard land pattern that ships with the
stock KiCad footprint libraries. Anything ambiguous returns None so the user
assigns it in KiCad rather than getting a silently wrong pad layout.
"""
from __future__ import annotations

import re

# Imperial chip size -> KiCad metric suffix used in stock library names.
_CHIP_SIZES = {
    "0201": "0201_0603Metric",
    "0402": "0402_1005Metric",
    "0603": "0603_1608Metric",
    "0805": "0805_2012Metric",
    "1206": "1206_3216Metric",
    "1210": "1210_3225Metric",
    "1812": "1812_4532Metric",
    "2010": "2010_5025Metric",
    "2512": "2512_6332Metric",
}

# Reference-designator prefix -> (KiCad library, symbol letter) for chip passives.
_CHIP_PREFIXES = {
    "R": ("Resistor_SMD", "R"),
    "C": ("Capacitor_SMD", "C"),
    "L": ("Inductor_SMD", "L"),
    "D": ("Diode_SMD", "D"),
    "LED": ("LED_SMD", "LED"),
    "FB": ("Inductor_SMD", "L"),
}

# Exact package names with a single unambiguous stock footprint.
_EXACT = {
    "SOT-23": "Package_TO_SOT_SMD:SOT-23",
    "SOT-23-3": "Package_TO_SOT_SMD:SOT-23",
    "SOT-23-5": "Package_TO_SOT_SMD:SOT-23-5",
    "SOT-23-6": "Package_TO_SOT_SMD:SOT-23-6",
    "SOT-323": "Package_TO_SOT_SMD:SOT-323_SC-70",
    "SOT-89": "Package_TO_SOT_SMD:SOT-89-3",
    "SOT-89-3": "Package_TO_SOT_SMD:SOT-89-3",
    "SOT-223": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SOT-223-3": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SOD-123": "Diode_SMD:D_SOD-123",
    "SOD-323": "Diode_SMD:D_SOD-323",
    "SOD-523": "Diode_SMD:D_SOD-523",
    "SMA": "Diode_SMD:D_SMA",
    "SMB": "Diode_SMD:D_SMB",
    "SMC": "Diode_SMD:D_SMC",
    "DO-214AC": "Diode_SMD:D_SMA",
    "DO-214AA": "Diode_SMD:D_SMB",
    "DO-214AB": "Diode_SMD:D_SMC",
    "TO-252": "Package_TO_SOT_SMD:TO-252-2",
    "TO-252-2": "Package_TO_SOT_SMD:TO-252-2",
    "TO-252-3": "Package_TO_SOT_SMD:TO-252-3",
    "TO-263": "Package_TO_SOT_SMD:TO-263-2",
    "TO-263-2": "Package_TO_SOT_SMD:TO-263-2",
    "SOIC-8": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "SOIC-14": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    "SOIC-16": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
    "SOP-8": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "MSOP-8": "Package_SO:MSOP-8_3x3mm_P0.65mm",
    "TSSOP-8": "Package_SO:TSSOP-8_4.4x3mm_P0.65mm",
    "TSSOP-14": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
    "TSSOP-16": "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
    "TSSOP-20": "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
    "LQFP-32": "Package_QFP:LQFP-32_7x7mm_P0.8mm",
    "LQFP-48": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
    "LQFP-64": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
    "LQFP-100": "Package_QFP:LQFP-100_14x14mm_P0.5mm",
    "SOT-563": "Package_TO_SOT_SMD:SOT-563",
    "SC-70-5": "Package_TO_SOT_SMD:SOT-353_SC-70-5",
    "SOT-353": "Package_TO_SOT_SMD:SOT-353_SC-70-5",
}


def _normalize(package: str) -> str:
    pkg = package.strip().upper()
    # "SOT-23(SOT-23-3)" style annotations -> first token.
    pkg = re.split(r"[(\s]", pkg)[0]
    return pkg


def map_package_to_footprint(
    package: str,
    reference: str = "",
    mpn: str = "",
) -> str | None:
    """Best-effort KiCad footprint ID for a package string, or None.

    `reference` disambiguates chip sizes shared by Rs, Cs, Ls, and diodes
    (an '0603' is a different library for C1 than for R1).
    """
    if not package:
        return None
    pkg = _normalize(package)

    if pkg in _EXACT:
        return _EXACT[pkg]

    # Chip passives: bare imperial size, optionally prefixed (e.g. "R0603").
    size_match = re.fullmatch(r"(?:[RCL])?(\d{4})", pkg)
    if size_match and size_match.group(1) in _CHIP_SIZES:
        suffix = _CHIP_SIZES[size_match.group(1)]
        ref_prefix = re.match(r"[A-Za-z]+", reference or "")
        prefix = (ref_prefix.group(0).upper() if ref_prefix else "")
        lib, letter = _CHIP_PREFIXES.get(prefix, (None, None))
        if lib is None:
            # No usable reference; only resistors are a safe default for a
            # bare size when the package itself spells the type (R0603).
            type_letter = pkg[0] if pkg[0] in ("R", "C", "L") else None
            if type_letter:
                lib, letter = _CHIP_PREFIXES[type_letter]
            else:
                return None
        return f"{lib}:{letter}_{suffix}"

    return None
