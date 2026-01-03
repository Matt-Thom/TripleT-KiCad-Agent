from backend.services.lcsc import lcsc_service
from backend.services.schematic import schematic_service

# Tool Definitions for LiteLLM / OpenAI format
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_lcsc",
            "description": "Search for electronic components on LCSC/JLCPCB to check stock, price, and specs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term (e.g., 'STM32F4', '10k resistor', 'USB-C connector')."
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
        results = await lcsc_service.search(args["query"])
        # Limit to top 3 to save context window
        return str([p.model_dump() for p in results[:3]])
        
    elif name == "generate_schematic":
        # Returns a file path
        path = schematic_service.generate_single_component_sch(args["mpn"], args["supplier_id"])
        return f"Schematic generated successfully at: {path}. Tell the user they can download it using the 'Generate Schematic' button in the search results or via the API."
        
    return "Error: Tool not found."
