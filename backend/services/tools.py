import os
from backend.services.lcsc import lcsc_service
from backend.services.schematic import schematic_service

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
            "name": "generate_schematic",
            "description": "Generate a KiCad 9 schematic file for a specific component. Use this when the user wants to 'create', 'make', or 'download' a schematic for a part.",
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
                    }
                },
                "required": ["mpn", "supplier_id"]
            }
        }
    }
]

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
        path = schematic_service.generate_single_component_sch(
            args["mpn"], args["supplier_id"],
            description=args.get("description", ""),
        )
        filename = os.path.basename(path)
        download_url = f"http://localhost:8000/api/download/{filename}"
        return f"Schematic generated. Download Link: [Download {args['mpn']} Schematic]({download_url})"
        
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

    return "Error: Tool not found."
