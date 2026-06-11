from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from backend.services.lcsc import lcsc_service, Part
from backend.services.schematic import schematic_service
from backend.services.ai import ai_service
from backend.routers import settings
from backend.routers import projects as projects_router
from backend.routers.projects import _ensure_default_project
from backend.db import init_db, get_session
from backend.models.project import Message, Project
from typing import List
import os
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TripleT KiCad Agent")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# Include Routers
app.include_router(settings.router, prefix="/api")
app.include_router(projects_router.router, prefix="/api")


@app.on_event("startup")
async def _on_startup() -> None:
    await init_db()

# Models for Chat
class ChatMessage(BaseModel):
    role: str
    content: str | None = None # Allow null content for tool calls
    
    class Config:
        extra = "allow" # Allow extra fields like 'tool_calls', 'function_call', 'name', 'tool_call_id'

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    project_id: int | None = None

# CORS Configuration
origins = [
    "http://localhost:5173", # Vite Dev Server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to TripleT KiCad Agent API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/search/lcsc", response_model=List[Part])
async def search_lcsc(q: str):
    """
    Search for components on LCSC (via jlcsearch API).
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    results = await lcsc_service.search(q)
    return results

@app.post("/api/generate/schematic")
async def generate_schematic(mpn: str, supplier_id: str):
    """
    Generate a KiCad schematic for a specific component.
    """
    try:
        file_path = schematic_service.generate_single_component_sch(mpn, supplier_id)
        if os.path.exists(file_path):
            return FileResponse(
                path=file_path, 
                filename=os.path.basename(file_path),
                media_type='application/octet-stream'
            )
        else:
            logger.error("Failed to generate schematic file: File not found after generation.")
            raise HTTPException(status_code=500, detail="Failed to generate schematic file")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating schematic: {e}", exc_info=True)
        # Re-raise generic error to be caught by global handler or return 500 here
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    base_dir = os.path.abspath("generated_schematics")
    file_path = os.path.abspath(os.path.join(base_dir, filename))

    # Prevent path traversal
    if os.path.commonpath([base_dir, file_path]) != base_dir:
        raise HTTPException(status_code=403, detail="Access denied")

    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type='application/octet-stream'
        )
    raise HTTPException(status_code=404, detail="File not found")

async def _default_project_id() -> int:
    async with get_session() as session:
        project = await _ensure_default_project(session)
        assert project.id is not None
        return project.id


async def _validated_project_id(project_id: int | None) -> int:
    """Return project_id if it exists, otherwise the default project's id."""
    if project_id is not None:
        async with get_session() as session:
            if await session.get(Project, project_id) is not None:
                return project_id
    return await _default_project_id()


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Send messages to the AI Agent.
    """
    # Convert Pydantic models to list of dicts for LiteLLM
    messages = [m.model_dump() for m in request.messages]

    # Ground the AI in KiCad 9 context and the full board-design workflow.
    system_prompt = {
        "role": "system",
        "content": (
            "You are the TripleT KiCad Agent, an expert in electronics design and KiCad 9. "
            "Help the user design circuits, select components, and understand electronics theory. "
            "Be concise, technical, and accurate. Always prioritize safety and best practices.\n\n"
            "BOARD DESIGN WORKFLOW — when the user asks to design a circuit/board (not just a "
            "single part), drive this sequence with tools, persisting state at each step:\n"
            "1. ARCHITECT: Decompose the requirements into logical blocks and interconnects with "
            "`update_block_diagram` (use `get_block_diagram` to read back the current plan).\n"
            "2. SOURCE: Pick real parts for each block with `search_lcsc` (one component per call). "
            "Note each part's `supplier_part_number`, `datasheet_url`, and Package attribute.\n"
            "3. PINOUT: For each IC, call `extract_pinout` with the part's `datasheet_url` to get "
            "real pins. Two-pin passives don't need this.\n"
            "4. CONNECT: Build the netlist with `update_schematic_ir` — components (reference, mpn, "
            "supplier_id, package, pins) and nets connecting specific pins. Include decoupling caps, "
            "pull-ups, and other supporting passives. Set `package` so footprints get auto-assigned.\n"
            "5. VERIFY: Run `run_erc` and fix every violation by updating the IR.\n"
            "6. COMPILE: Call `compile_schematic_ir` to emit the KiCad project and give the user "
            "the download links.\n"
            "7. FABRICATE (optional): If the user wants native KiCad checks or fab outputs, call "
            "`export_fabrication_outputs` with the compiled schematic filename.\n\n"
            "TOOL USAGE RULES:\n"
            "1. For sourcing a specific MPN or supplier search, call `search_lcsc`.\n"
            "2. CRITICAL: For generating a schematic of ONE custom component, you MUST call "
            "`generate_schematic`. Do not describe the steps in text when the user asks to "
            "'generate', 'create', 'make', or 'download'. Pass `pins` from `extract_pinout` "
            "whenever a datasheet URL is available.\n"
            "3. For any STANDARD sub-circuit (LDO, USB-C, I2C pull-ups, reset, decoupling), "
            "FIRST call `lookup_pattern` to see if a verified pattern exists, THEN call "
            "`apply_pattern` with the id. Prefer verified patterns over custom generation.\n"
            "4. Schematics compiled from the IR assign KiCad footprints from each component's "
            "package; tell the user that 'Update PCB from Schematic' in KiCad starts the board "
            "layout, and that routing/DRC/Gerbers happen in KiCad."
        )
    }

    # Prepend system prompt if not already present
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, system_prompt)

    response_text = await ai_service.get_response(messages, project_id=request.project_id)

    # Persist the last user message and assistant reply to the active project.
    try:
        project_id = await _validated_project_id(request.project_id)
        last_user = next(
            (m for m in reversed(request.messages) if m.role == "user"), None
        )
        async with get_session() as session:
            if last_user is not None and last_user.content:
                session.add(
                    Message(
                        project_id=project_id,
                        role="user",
                        content=last_user.content,
                    )
                )
            session.add(
                Message(
                    project_id=project_id,
                    role="assistant",
                    content=response_text or "",
                )
            )
            await session.commit()
    except Exception as exc:  # pragma: no cover - persistence must not break chat
        logger.warning(f"Failed to persist chat messages: {exc}")

    return {"content": response_text}


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=True)
