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
        # Returns a file path
        path = schematic_service.generate_single_component_sch(args["mpn"], args["supplier_id"])
        filename = os.path.basename(path)
        download_url = f"http://localhost:8000/api/download/{filename}"
        return f"Schematic generated. Download Link: [Download {args['mpn']} Schematic]({download_url})"
        
    return "Error: Tool not found."
