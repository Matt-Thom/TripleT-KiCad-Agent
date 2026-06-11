"""Generate KiCad 9 schematics using kicad_sch_api plus a SymbolResolver."""
from __future__ import annotations

import json
import logging
import math
import os
import re
import uuid as uuid_mod
from pathlib import Path
from typing import Optional

from backend.services.footprints import map_package_to_footprint
from backend.services.kicad_libs import LibraryIndex
from backend.services.procedural_symbol import PinSpec, build_procedural_symbol
from backend.services.symbol_resolver import SymbolResolver
from backend.models.schematic_ir import SchematicIRData

logger = logging.getLogger(__name__)


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


def _symbol_name(mpn: str) -> str:
    """A lib_id-safe symbol name (':' is the library separator)."""
    return mpn.replace(":", "_").replace('"', "'") or "PART"


class SchematicService:
    # Placement grid for multi-component sheets (mm, multiples of 1.27).
    _COL_PITCH = 50.8
    _COLUMNS = 4
    _ROW_MARGIN = 25.4

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
            f'  (uuid "{uuid_mod.uuid4()}")\n'
            '  (paper "A4")\n'
            f'{body}\n'
            '  (sheet_instances (path "/" (page "1")))\n'
            ')\n'
        )

        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def generate_multi_component_sch(
        self,
        components: list[dict],
        filename: Optional[str] = None,
    ) -> str:
        import kicad_sch_api as ksa
        from kicad_sch_api.library.cache import get_symbol_cache
        from backend.services.procedural_symbol import VALID_PIN_TYPES

        # 1. Resolve symbols for all components
        resolver = self._resolver()
        cache = get_symbol_cache()

        # Ensure we have a valid output file path
        if not filename:
            filename = f"multi_component_{uuid_mod.uuid4().hex[:8]}.kicad_sch"
        else:
            filename = _sanitize_filename(filename)
            if not filename.endswith(".kicad_sch"):
                filename += ".kicad_sch"
        file_path = os.path.join(self.output_dir, filename)

        # Procedural symbols live in a persistent library named after the
        # schematic, kept next to it so KiCad can re-resolve lib_ids later.
        gen_lib_name = f"{Path(filename).stem}_symbols"

        processed_components = []
        procedural_symbols_to_write = []

        for comp in components:
            mpn = comp.get("mpn", "")
            reference = comp.get("reference", "")
            supplier_id = comp.get("supplier_id", "C1")
            description = comp.get("description", "")
            package = comp.get("package", "")
            footprint = comp.get("footprint") or map_package_to_footprint(
                package, reference=reference, mpn=mpn
            )

            # Map input pins dict to PinSpec if provided
            raw_pins = comp.get("pins", None)
            pins_spec_list = []
            if raw_pins:
                for p in raw_pins:
                    if isinstance(p, dict):
                        pins_spec_list.append(
                            PinSpec(
                                number=str(p["number"]),
                                name=p.get("name", f"Pin{p['number']}"),
                                type=p.get("type", "unspecified")
                            )
                        )
                    else:
                        pins_spec_list.append(p)
            else:
                # If no pins provided, check connections for pin numbers as keys
                conn = comp.get("connections", {})
                if conn:
                    for k in conn.keys():
                        pins_spec_list.append(
                            PinSpec(
                                number=str(k),
                                name=f"Pin{k}",
                                type="unspecified"
                            )
                        )

            resolved = resolver.resolve(mpn=mpn, description=description, pins=pins_spec_list or None)

            # Find the actual pins we will use
            final_pins = []
            if resolved.kind == "library":
                lib_id = f"{resolved.library}:{resolved.name}"
                # Try to load pins from symbol library
                symbol_def = cache.get_symbol(lib_id)
                if symbol_def:
                    for p in symbol_def.pins:
                        ptype = p.pin_type.value if hasattr(p.pin_type, "value") else str(p.pin_type)
                        if ptype not in VALID_PIN_TYPES:
                            ptype = "unspecified"
                        final_pins.append(
                            PinSpec(
                                number=p.number,
                                name=p.name,
                                type=ptype
                            )
                        )
                else:
                    # Fallback if library load fails
                    final_pins = [PinSpec(number="1", name="Pin1", type="unspecified")]
            else:
                # Procedural symbol
                lib_id = f"{gen_lib_name}:{_symbol_name(mpn)}"
                final_pins = resolved.pins
                procedural_symbols_to_write.append((mpn, final_pins))

            processed_components.append({
                "mpn": mpn,
                "reference": reference,
                "supplier_id": supplier_id,
                "lib_id": lib_id,
                "footprint": footprint,
                "pins": final_pins,
                "connections": comp.get("connections", {}),
            })

        # 2. Write the persistent symbol library when procedural symbols exist.
        gen_lib_file = Path(self.output_dir) / f"{gen_lib_name}.kicad_sym"
        if procedural_symbols_to_write:
            symbol_defs = []
            seen_names = set()
            for mpn, pins in procedural_symbols_to_write:
                name = _symbol_name(mpn)
                if name not in seen_names:
                    seen_names.add(name)
                    sexp = build_procedural_symbol(name=name, pins=pins)
                    symbol_defs.append(sexp)

            lib_content = (
                f"(kicad_symbol_lib (version 20231120) (generator TripleT-Agent)\n"
                f"  {''.join(symbol_defs)}"
                f")\n"
            )
            gen_lib_file.write_text(lib_content)
            # Drop any previously parsed symbols so a recompile of the same
            # schematic re-reads the rewritten library from disk.
            cache.clear_cache()
            cache.add_library_path(str(gen_lib_file.absolute()))

        # 3. Create schematic and place components on a wrapped grid.
        sch = ksa.create_schematic(Path(filename).stem)

        row_pin_max = 0
        x0, y = 101.6, 101.6
        for i, comp in enumerate(processed_components):
            col = i % self._COLUMNS
            if i and col == 0:
                # Advance to the next row, leaving room for the tallest
                # symbol in the finished row (height grows with pin count).
                row_height = math.ceil(row_pin_max / 2) * 2.54 + self._ROW_MARGIN
                y += max(self._COL_PITCH, row_height)
                row_pin_max = 0
            row_pin_max = max(row_pin_max, len(comp["pins"]))
            x = x0 + col * self._COL_PITCH
            try:
                sch.components.add(
                    lib_id=comp["lib_id"],
                    reference=comp["reference"],
                    value=comp["mpn"],
                    position=(x, y),
                    footprint=comp["footprint"],
                )
            except Exception as e:
                logger.warning(
                    "Failed to place %s (%s): %s", comp["reference"], comp["lib_id"], e
                )

        # 4. Connect nets with labels attached at each pin. Labels scale to
        # any net size and keep the sheet readable, unlike point-to-point wires.
        for comp in processed_components:
            ref = comp["reference"]
            conns = comp["connections"]
            pins = comp["pins"]

            for pin_key, net_name in conns.items():
                if not net_name:
                    continue
                # Resolve pin_key to pin_number
                pin_num = None
                for p in pins:
                    if p.number == str(pin_key):
                        pin_num = p.number
                        break
                if not pin_num:
                    for p in pins:
                        if p.name.lower() == str(pin_key).lower():
                            pin_num = p.number
                            break
                if not pin_num:
                    logger.warning(
                        "Net %s references unknown pin %r on %s", net_name, pin_key, ref
                    )
                    continue

                try:
                    sch.add_label(str(net_name), pin=(ref, pin_num))
                except Exception as e:
                    logger.warning(
                        "Failed to label net %s at %s.%s: %s", net_name, ref, pin_num, e
                    )

        # 5. Save schematic
        sch.save(file_path)
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
            f'    (uuid "{uuid_mod.uuid4()}")\n'
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
            f'    (uuid "{uuid_mod.uuid4()}")\n'
            f'    (property "Reference" "U1" (at 100 92 0))\n'
            f'    (property "Value" "{safe_value}" (at 100 94 0))\n'
            '  )'
        )

    def _ir_to_component_dicts(self, ir: SchematicIRData) -> list[dict]:
        components_list = []
        for comp in ir.components:
            # Build connections mapping for this component
            connections = {}
            for net in ir.nets:
                for conn in net.connections:
                    if conn.component_ref == comp.reference:
                        connections[conn.pin_number] = net.name

            comp_dict = {
                "mpn": comp.mpn,
                "supplier_id": comp.supplier_id,
                "reference": comp.reference,
                "description": comp.properties.get("description", ""),
                "package": comp.package,
                "footprint": comp.footprint
                or map_package_to_footprint(comp.package, reference=comp.reference, mpn=comp.mpn),
                "pins": [{"number": p.number, "name": p.name, "type": p.type} for p in comp.pins],
                "connections": connections,
            }
            components_list.append(comp_dict)
        return components_list

    def compile_ir_to_kicad_sch(
        self,
        ir: SchematicIRData,
        filename: Optional[str] = None,
    ) -> str:
        return self.generate_multi_component_sch(
            self._ir_to_component_dicts(ir), filename=filename
        )

    def compile_ir_to_project(
        self,
        ir: SchematicIRData,
        project_name: str = "triplet_project",
    ) -> dict[str, str]:
        """Compile the IR into a complete KiCad project.

        Emits `<name>.kicad_sch`, a minimal `<name>.kicad_pro`, and — when
        procedural symbols were generated — `<name>_symbols.kicad_sym` plus a
        project-local `sym-lib-table` so KiCad resolves the generated lib_ids.
        With footprints assigned, "Update PCB from Schematic" works directly.

        Returns a mapping of artifact kind -> file path.
        """
        stem = _sanitize_filename(project_name)
        if stem.endswith(".kicad_sch"):
            stem = stem[: -len(".kicad_sch")]

        sch_path = self.compile_ir_to_kicad_sch(ir, filename=f"{stem}.kicad_sch")
        files: dict[str, str] = {"schematic": sch_path}

        pro_path = os.path.join(self.output_dir, f"{stem}.kicad_pro")
        with open(pro_path, "w") as f:
            json.dump(self._minimal_project_dict(stem, sch_path), f, indent=2)
        files["project"] = pro_path

        lib_path = Path(self.output_dir) / f"{stem}_symbols.kicad_sym"
        if lib_path.exists():
            files["symbol_library"] = str(lib_path)
            # Project-local table; ${KIPRJMOD} keeps it relocatable. One
            # project per output directory — later compiles overwrite it.
            table_path = Path(self.output_dir) / "sym-lib-table"
            table_path.write_text(
                "(sym_lib_table\n"
                "  (version 7)\n"
                f'  (lib (name "{stem}_symbols")(type "KiCad")'
                f'(uri "${{KIPRJMOD}}/{stem}_symbols.kicad_sym")'
                '(options "")(descr "TripleT generated symbols"))\n'
                ")\n"
            )
            files["sym_lib_table"] = str(table_path)

        return files

    @staticmethod
    def _minimal_project_dict(stem: str, sch_path: str) -> dict:
        root_uuid = ""
        try:
            import kicad_sch_api as ksa

            root_uuid = str(ksa.load_schematic(sch_path).uuid)
        except Exception:
            pass
        project = {
            "board": {"design_settings": {}, "layer_presets": [], "viewports": []},
            "boards": [],
            "cvpcb": {"equivalence_files": []},
            "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
            "meta": {"filename": f"{stem}.kicad_pro", "version": 3},
            "pcbnew": {"last_paths": {}},
            "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
            "sheets": [[root_uuid, "Root"]] if root_uuid else [],
            "text_variables": {},
        }
        return project


schematic_service = SchematicService()
