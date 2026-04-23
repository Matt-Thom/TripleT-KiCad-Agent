"""Generate KiCad 9 schematics using kicad_sch_api plus a SymbolResolver."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from backend.services.kicad_libs import LibraryIndex
from backend.services.procedural_symbol import PinSpec, build_procedural_symbol
from backend.services.symbol_resolver import SymbolResolver


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^\w\-\.]", "_", name)
    # Never allow a leading dot-segment like "..".
    safe = safe.lstrip(".")
    return safe or "unnamed"


def _escape_sexp(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\x00", "")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


class SchematicService:
    def __init__(
        self,
        output_dir: str = "generated_schematics",
        sym_lib_table_env: str = "KICAD_SYM_LIB_TABLE",
    ) -> None:
        self.output_dir = output_dir
        self._sym_lib_table_env = sym_lib_table_env
        os.makedirs(self.output_dir, exist_ok=True)

    def _resolver(self) -> SymbolResolver:
        table_path = os.environ.get(self._sym_lib_table_env)
        index: Optional[LibraryIndex] = None
        if table_path and Path(table_path).is_file():
            try:
                index = LibraryIndex.from_table(Path(table_path))
            except Exception:
                index = None
        return SymbolResolver(index=index)

    def generate_single_component_sch(
        self,
        mpn: str,
        supplier_id: str,
        *,
        description: str = "",
        pins: Optional[list[PinSpec]] = None,
    ) -> str:
        safe_mpn = _sanitize_filename(mpn)
        safe_supplier = _sanitize_filename(supplier_id)
        filename = f"{safe_mpn}_{safe_supplier}.kicad_sch"
        file_path = os.path.join(self.output_dir, filename)

        resolver = self._resolver()
        resolved = resolver.resolve(mpn=mpn, description=description, pins=pins)

        if resolved.kind == "library":
            lib_id = f'{resolved.library}:{resolved.name}'
            # Reference an existing library symbol; no lib_symbols block needed if KiCad
            # can reach the library at load time, but for portability include a stub.
            body = self._render_library_ref(lib_id=lib_id, value=mpn)
        else:
            body = self._render_procedural(mpn=mpn, pins=resolved.pins)

        content = (
            '(kicad_sch\n'
            '  (version 20250114)\n'
            '  (generator "TripleT-Agent")\n'
            '  (uuid "33694086-6638-4672-8418-1850388e3609")\n'
            '  (paper "A4")\n'
            f'{body}\n'
            '  (sheet_instances (path "/" (page "1")))\n'
            ')\n'
        )

        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def apply_pattern(self, pattern_id: str, inputs: dict) -> str:
        from backend.knowledge.registry import PatternRegistry
        import kicad_sch_api as ksa

        registry = PatternRegistry.discover()
        pat = registry.get(pattern_id)
        if pat is None:
            raise ValueError(f"Unknown pattern_id: {pattern_id}")

        sch = ksa.create_schematic(pattern_id)
        pat.apply(sch, **inputs)

        safe = _sanitize_filename(pattern_id)
        file_path = os.path.join(self.output_dir, f"{safe}.kicad_sch")
        sch.save(file_path)
        return file_path

    @staticmethod
    def _render_procedural(*, mpn: str, pins: list[PinSpec]) -> str:
        symbol_sexp = build_procedural_symbol(name=mpn, pins=pins)
        lib_id = _escape_sexp(mpn)
        placed = (
            f'  (symbol (lib_id "{lib_id}") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid "00000000-0000-0000-0000-000000000001")\n'
            f'    (property "Reference" "U1" (at 100 92 0))\n'
            f'    (property "Value" "{lib_id}" (at 100 94 0))\n'
            '  )'
        )
        # Indent the symbol definition into a lib_symbols block
        indented = "\n".join("    " + line for line in symbol_sexp.strip().splitlines())
        return f'  (lib_symbols\n{indented}\n  )\n{placed}'

    @staticmethod
    def _render_library_ref(*, lib_id: str, value: str) -> str:
        safe_value = _escape_sexp(value)
        safe_lib_id = _escape_sexp(lib_id)
        # Empty lib_symbols block — KiCad resolves lib_id against sym-lib-table at load time
        return (
            '  (lib_symbols)\n'
            f'  (symbol (lib_id "{safe_lib_id}") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid "00000000-0000-0000-0000-000000000001")\n'
            f'    (property "Reference" "U1" (at 100 92 0))\n'
            f'    (property "Value" "{safe_value}" (at 100 94 0))\n'
            '  )'
        )


schematic_service = SchematicService()
