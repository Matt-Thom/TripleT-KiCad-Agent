"""Generate KiCad 9 schematics using kicad_sch_api plus a SymbolResolver."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from backend.services.kicad_libs import LibraryIndex
from backend.services.procedural_symbol import PinSpec, build_procedural_symbol
from backend.services.symbol_resolver import SymbolResolver
from backend.models.schematic_ir import SchematicIRData


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

    def generate_multi_component_sch(
        self,
        components: list[dict],
        filename: Optional[str] = None,
    ) -> str:
        import kicad_sch_api as ksa
        import uuid
        from backend.services.procedural_symbol import VALID_PIN_TYPES

        # 1. Resolve symbols for all components
        resolver = self._resolver()
        cache = ksa.get_symbol_cache()

        processed_components = []
        procedural_symbols_to_write = []
        temp_lib_name = f"temp_lib_{uuid.uuid4().hex}"
        
        # Ensure we have a valid output file path
        if not filename:
            filename = f"multi_component_{uuid.uuid4().hex[:8]}.kicad_sch"
        else:
            filename = _sanitize_filename(filename)
            if not filename.endswith(".kicad_sch"):
                filename += ".kicad_sch"
        file_path = os.path.join(self.output_dir, filename)

        for comp in components:
            mpn = comp.get("mpn", "")
            reference = comp.get("reference", "")
            supplier_id = comp.get("supplier_id", "C1")
            description = comp.get("description", "")
            
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
                lib_id = f"{temp_lib_name}:{mpn}"
                final_pins = resolved.pins
                procedural_symbols_to_write.append((mpn, final_pins))
                
            processed_components.append({
                "mpn": mpn,
                "reference": reference,
                "supplier_id": supplier_id,
                "lib_id": lib_id,
                "pins": final_pins,
                "connections": comp.get("connections", {}),
            })

        # 2. Write and register temporary symbol library if needed
        temp_lib_file = None
        if procedural_symbols_to_write:
            temp_lib_file = Path(self.output_dir) / f"{temp_lib_name}.kicad_sym"
            symbol_defs = []
            seen_mpns = set()
            for mpn, pins in procedural_symbols_to_write:
                if mpn not in seen_mpns:
                    seen_mpns.add(mpn)
                    sexp = build_procedural_symbol(name=mpn, pins=pins)
                    symbol_defs.append(sexp)
            
            lib_content = (
                f"(kicad_symbol_lib (version 20231120) (generator TripleT-Agent)\n"
                f"  {''.join(symbol_defs)}"
                f")\n"
            )
            temp_lib_file.write_text(lib_content)
            cache.add_library_path(str(temp_lib_file.absolute()))

        # 3. Create schematic and add components side-by-side
        sch = ksa.create_schematic("multi-component")
        
        # Grid snapping coordinates
        # First component at (101.6, 101.6). Grid is 2.54mm.
        for i, comp in enumerate(processed_components):
            x = 101.6 + i * 50.8
            y = 101.6
            sch.components.add(
                lib_id=comp["lib_id"],
                reference=comp["reference"],
                value=comp["mpn"],
                position=(x, y),
            )

        # 4. Perform orthogonal wiring for matching nets
        # Group pins by net name
        nets = {}
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
                
                if pin_num:
                    nets.setdefault(net_name, []).append((ref, pin_num))

        # Wire each net sequentially (daisy chain)
        for net_name, pin_list in nets.items():
            if len(pin_list) < 2:
                continue
            for j in range(len(pin_list) - 1):
                comp1_ref, pin1_num = pin_list[j]
                comp2_ref, pin2_num = pin_list[j+1]
                try:
                    sch.auto_route_pins(
                        comp1_ref,
                        pin1_num,
                        comp2_ref,
                        pin2_num,
                        routing_strategy="manhattan",
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to route net {net_name} between {comp1_ref}.{pin1_num} and {comp2_ref}.{pin2_num}: {e}"
                    )

        # 5. Save schematic
        sch.save(file_path)

        # 6. Cleanup temporary library
        if temp_lib_file:
            abs_path = temp_lib_file.absolute()
            if abs_path in cache._library_paths:
                cache._library_paths.remove(abs_path)
            if temp_lib_file.exists():
                temp_lib_file.unlink()

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

    def compile_ir_to_kicad_sch(
        self,
        ir: SchematicIRData,
        filename: Optional[str] = None,
    ) -> str:
        # Translate SchematicIRData to components dictionary list expected by generate_multi_component_sch
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
                "pins": [{"number": p.number, "name": p.name, "type": p.type} for p in comp.pins],
                "connections": connections,
            }
            components_list.append(comp_dict)
            
        return self.generate_multi_component_sch(components_list, filename=filename)


schematic_service = SchematicService()
