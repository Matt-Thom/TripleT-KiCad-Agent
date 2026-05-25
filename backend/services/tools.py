import json
import os

from backend.services.datasheet import DatasheetError
from backend.services.lcsc import lcsc_service
from backend.services.pinout import PinoutExtractionError, extract_pinout
from backend.services.procedural_symbol import VALID_PIN_TYPES, PinSpec
from backend.services.schematic import schematic_service
from backend.db import get_session
from sqlmodel import select
from backend.models.project import Project, BlockDiagram, SchematicIR
from backend.models.schematic_ir import BlockDiagramData, SchematicIRData
from backend.services.erc import erc_service

# Tool Definitions for LiteLLM / OpenAI format
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_lcsc",
            "description": "Search for electronic components on LCSC/JLCPCB. IMPORTANT: Search for ONE component at a time. If the user asks for multiple parts (e.g., 'STM32 and KX134'), call this tool twice: once for 'STM32' and once for 'KX134'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term for A SINGLE component (e.g., 'STM32F4', 'KX134')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_pattern",
            "description": (
                "Search the library of verified circuit patterns (LDO, USB-C, I2C pull-ups, "
                "MCU reset, etc.) by natural-language query. Call this BEFORE apply_pattern "
                "whenever the user asks for a standard sub-circuit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the user wants (e.g. '3.3V regulator')."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_pattern",
            "description": (
                "Apply a known circuit pattern by id, using inputs discovered via lookup_pattern. "
                "Returns a downloadable KiCad 9 schematic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern_id": {"type": "string", "description": "Pattern id from lookup_pattern."},
                    "inputs": {
                        "type": "object",
                        "description": "Pattern-specific inputs (see lookup_pattern result for keys).",
                        "additionalProperties": True
                    }
                },
                "required": ["pattern_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_pinout",
            "description": (
                "Fetch a datasheet PDF and extract the component's pinout as a structured "
                "list of pins. Use this BEFORE generate_schematic when the user wants a real "
                "multi-pin symbol (not a placeholder) and a datasheet URL is available — "
                "typically from the `datasheet_url` field of a search_lcsc result. "
                "Returns pins you can pass directly to generate_schematic via the `pins` arg."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "datasheet_url": {
                        "type": "string",
                        "description": "URL of the datasheet PDF."
                    },
                    "mpn": {
                        "type": "string",
                        "description": "Manufacturer part number, used as context for the extractor."
                    }
                },
                "required": ["datasheet_url", "mpn"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_schematic",
            "description": "Generate a KiCad 9 schematic file for a specific component. Use this when the user wants to 'create', 'make', or 'download' a schematic for a part. Pass `pins` (from extract_pinout) to get a real multi-pin symbol; omit to fall back to library reuse or a 1-pin placeholder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mpn": {
                        "type": "string",
                        "description": "The Manufacturer Part Number (e.g., 'STM32F103C8T6')."
                    },
                    "supplier_id": {
                        "type": "string",
                        "description": "The LCSC Part Number (e.g., 'C8734')."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional part description to improve library-symbol lookup."
                    },
                    "pins": {
                        "type": "array",
                        "description": (
                            "Optional pin list. Usually obtained by calling extract_pinout first. "
                            "If provided, a procedural symbol is drawn from these pins instead of "
                            "using a library symbol or placeholder."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "number": {"type": "string"},
                                "name": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": sorted(VALID_PIN_TYPES),
                                },
                            },
                            "required": ["number", "name", "type"],
                        },
                    },
                },
                "required": ["mpn", "supplier_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_multi_component_schematic",
            "description": "Generate a KiCad 9 schematic containing multiple components placed side-by-side with orthogonal/Manhattan wire routing between matching nets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "components": {
                        "type": "array",
                        "description": "The list of components to place in the schematic.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "mpn": {
                                    "type": "string",
                                    "description": "Manufacturer Part Number (e.g. 'AMS1117-3.3')."
                                },
                                "supplier_id": {
                                    "type": "string",
                                    "description": "Supplier ID / LCSC Part Number (e.g. 'C8734')."
                                },
                                "reference": {
                                    "type": "string",
                                    "description": "Unique component reference designator (e.g. 'U1', 'C1')."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional component description."
                                },
                                "pins": {
                                    "type": "array",
                                    "description": "Optional pin definitions for procedural symbols.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "number": {"type": "string"},
                                            "name": {"type": "string"},
                                            "type": {
                                                "type": "string",
                                                "enum": sorted(VALID_PIN_TYPES)
                                            }
                                        },
                                        "required": ["number", "name", "type"]
                                    }
                                },
                                "connections": {
                                    "type": "object",
                                    "description": "Mapping from pin numbers or pin names to net names (e.g. {'1': 'GND', '2': '3V3'}). Matching nets will be automatically connected with wires.",
                                    "additionalProperties": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["mpn", "reference"]
                        }
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional output schematic filename."
                    }
                },
                "required": ["components"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_block_diagram",
            "description": "Create or update the logical architecture block diagram for the active project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "voltage_domain": {"type": "string"}
                            },
                            "required": ["id", "type"]
                        }
                    },
                    "connections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_block_id": {"type": "string"},
                                "target_block_id": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"}
                            },
                            "required": ["source_block_id", "target_block_id"]
                        }
                    }
                },
                "required": ["blocks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_block_diagram",
            "description": "Get the current logical block diagram for the active project."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_schematic_ir",
            "description": "Add, modify, or connect components directly in the structural Netlist IR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "components": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "reference": {"type": "string"},
                                "mpn": {"type": "string"},
                                "supplier_id": {"type": "string"},
                                "value": {"type": "string"},
                                "pins": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "number": {"type": "string"},
                                            "name": {"type": "string"},
                                            "type": {"type": "string"}
                                        },
                                        "required": ["number", "name", "type"]
                                    }
                                },
                                "block_id": {"type": "string"}
                            },
                            "required": ["reference", "mpn", "supplier_id"]
                        }
                    },
                    "nets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "connections": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "component_ref": {"type": "string"},
                                            "pin_number": {"type": "string"}
                                        },
                                        "required": ["component_ref", "pin_number"]
                                    }
                                }
                            },
                            "required": ["name", "connections"]
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_schematic_ir",
            "description": "Get the current structural Schematic/Netlist IR."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_erc",
            "description": "Run the Electrical Rules Check on the structural Netlist IR and report any violations."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compile_schematic_ir",
            "description": "Compiles the active project's Netlist IR into a native KiCad 9 (.kicad_sch) file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Optional custom output schematic filename."}
                }
            }
        }
    }
]


def _coerce_pins(raw: object) -> list[PinSpec] | None:
    if not raw:
        return None
    if not isinstance(raw, list):
        return None
    pins: list[PinSpec] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            pins.append(
                PinSpec(
                    number=str(entry["number"]),
                    name=str(entry["name"]),
                    type=str(entry["type"]).lower(),
                )
            )
        except (KeyError, ValueError):
            continue
    return pins or None


async def execute_tool(name: str, args: dict):
    """
    Executes a tool by name with the provided arguments.
    """
    if name == "search_lcsc":
        # Returns a list of Part objects, we need to serialize them to text/json for the AI
        try:
            results = await lcsc_service.search(args["query"])
            if not results:
                return f"No results found for query: '{args['query']}'. Try a broader search term."
            # Limit to top 3 to save context window
            return str([p.model_dump() for p in results[:3]])
        except Exception as e:
            return f"Error searching for '{args['query']}': {str(e)}"

    elif name == "generate_schematic":
        pins = _coerce_pins(args.get("pins"))
        path = schematic_service.generate_single_component_sch(
            args["mpn"], args["supplier_id"],
            description=args.get("description", ""),
            pins=pins,
        )
        filename = os.path.basename(path)
        download_url = f"/api/download/{filename}"
        return f"Schematic generated. Download Link: [Download {args['mpn']} Schematic]({download_url})"

    elif name == "generate_multi_component_schematic":
        path = schematic_service.generate_multi_component_sch(
            args["components"],
            filename=args.get("filename"),
        )
        filename = os.path.basename(path)
        download_url = f"/api/download/{filename}"
        return f"Multi-component schematic generated. Download Link: [Download Schematic]({download_url})"

    elif name == "lookup_pattern":
        from backend.knowledge.registry import PatternRegistry, PatternRetriever
        registry = PatternRegistry.discover()
        retriever = PatternRetriever(registry)
        hits = retriever.search(args["query"], top_k=3)
        summary = [
            {
                "id": p.metadata.id,
                "title": p.metadata.title,
                "description": p.metadata.description,
                "inputs": p.metadata.inputs,
            }
            for p in hits
        ]
        return str(summary) if summary else "No matching patterns. Suggest using search_lcsc and generate_schematic instead."

    elif name == "apply_pattern":
        try:
            path = schematic_service.apply_pattern(
                args["pattern_id"], args.get("inputs", {})
            )
            filename = os.path.basename(path)
            return f"Pattern applied. [Download {filename}](/api/download/{filename})"
        except ValueError as e:
            # Unknown pattern id
            return f"Error: {e}"
        except Exception as e:
            # Pattern misconfigured — corrupt lib_id, failed save, etc.
            return f"Error applying pattern '{args['pattern_id']}': {type(e).__name__}: {e}"

    elif name == "extract_pinout":
        try:
            pins = await extract_pinout(args["datasheet_url"], args["mpn"])
        except DatasheetError as e:
            return f"Error fetching datasheet: {e}"
        except PinoutExtractionError as e:
            return f"Error extracting pinout: {e}"
        except Exception as e:
            return f"Error in extract_pinout: {type(e).__name__}: {e}"
        return json.dumps(
            [{"number": p.number, "name": p.name, "type": p.type} for p in pins]
        )

    elif name == "get_block_diagram":
        pid = await _get_default_project_id()
        async with get_session() as session:
            result = await session.execute(
                select(BlockDiagram).where(BlockDiagram.project_id == pid)
            )
            bd = result.scalars().first()
            if bd is None:
                return "Block diagram is currently empty."
            return json.dumps({"blocks": bd.blocks, "connections": bd.connections})

    elif name == "update_block_diagram":
        pid = await _get_default_project_id()
        blocks = args.get("blocks", [])
        connections = args.get("connections", [])
        async with get_session() as session:
            result = await session.execute(
                select(BlockDiagram).where(BlockDiagram.project_id == pid)
            )
            bd = result.scalars().first()
            if bd is None:
                bd = BlockDiagram(project_id=pid, blocks=blocks, connections=connections)
                session.add(bd)
            else:
                bd.blocks = blocks
                bd.connections = connections
                from datetime import datetime
                bd.updated_at = datetime.utcnow()
                session.add(bd)
            await session.commit()
        return "Block diagram updated successfully."

    elif name == "get_schematic_ir":
        pid = await _get_default_project_id()
        async with get_session() as session:
            result = await session.execute(
                select(SchematicIR).where(SchematicIR.project_id == pid)
            )
            sir = result.scalars().first()
            if sir is None:
                return "Schematic IR is currently empty."
            return json.dumps({"components": sir.components, "nets": sir.nets})

    elif name == "update_schematic_ir":
        pid = await _get_default_project_id()
        components = args.get("components", [])
        nets = args.get("nets", [])
        async with get_session() as session:
            result = await session.execute(
                select(SchematicIR).where(SchematicIR.project_id == pid)
            )
            sir = result.scalars().first()
            if sir is None:
                sir = SchematicIR(project_id=pid, components=components, nets=nets)
                session.add(sir)
            else:
                if components:
                    sir.components = components
                if nets:
                    sir.nets = nets
                from datetime import datetime
                sir.updated_at = datetime.utcnow()
                session.add(sir)
            await session.commit()
        return "Schematic IR updated successfully."

    elif name == "run_erc":
        pid = await _get_default_project_id()
        async with get_session() as session:
            result = await session.execute(
                select(SchematicIR).where(SchematicIR.project_id == pid)
            )
            sir = result.scalars().first()
            if sir is None:
                return "Schematic IR is empty. No ERC checks can be run."
            ir_data = SchematicIRData(components=sir.components, nets=sir.nets)
            violations = erc_service.check(ir_data)
            if not violations:
                return "ERC completed successfully: No violations found!"
            return json.dumps([v.model_dump() for v in violations])

    elif name == "compile_schematic_ir":
        pid = await _get_default_project_id()
        async with get_session() as session:
            result = await session.execute(
                select(SchematicIR).where(SchematicIR.project_id == pid)
            )
            sir = result.scalars().first()
            if sir is None or not sir.components:
                return "Error: Cannot compile empty Schematic IR."
            ir_data = SchematicIRData(components=sir.components, nets=sir.nets)
            try:
                path = schematic_service.compile_ir_to_kicad_sch(ir_data, filename=args.get("filename"))
                filename = os.path.basename(path)
                download_url = f"/api/download/{filename}"
                return f"Schematic successfully compiled from IR. [Download Schematic]({download_url})"
            except Exception as e:
                return f"Error compiling Schematic IR: {e}"

    return "Error: Tool not found."


async def _get_default_project_id() -> int:
    from backend.routers.projects import DEFAULT_PROJECT_NAME
    async with get_session() as session:
        result = await session.execute(
            select(Project).where(Project.name == DEFAULT_PROJECT_NAME)
        )
        project = result.scalars().first()
        if project is None:
            project = Project(name=DEFAULT_PROJECT_NAME)
            session.add(project)
            await session.commit()
            await session.refresh(project)
        return project.id
