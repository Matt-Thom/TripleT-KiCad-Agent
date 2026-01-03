from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.services.lcsc import lcsc_service, Part
from backend.services.schematic import schematic_service
from backend.services.ai import ai_service
from backend.routers import settings
from typing import List
import os

app = FastAPI(title="TripleT KiCad Agent")

# Include Routers
app.include_router(settings.router, prefix="/api")

# Models for Chat
class ChatMessage(BaseModel):
    role: str
    content: str | None = None # Allow null content for tool calls
    
    class Config:
        extra = "allow" # Allow extra fields like 'tool_calls', 'function_call', 'name', 'tool_call_id'

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

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
            raise HTTPException(status_code=500, detail="Failed to generate schematic file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("generated_schematics", filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type='application/octet-stream'
        )
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Send messages to the AI Agent.
    """
    # Convert Pydantic models to list of dicts for LiteLLM
    messages = [m.model_dump() for m in request.messages]
    
    # We should add a System Prompt here to ground the AI in KiCad 9 context
    system_prompt = {
        "role": "system",
        "content": (
            "You are the TripleT KiCad Agent, an expert in electronics design and KiCad 9. "
            "Help the user design circuits, select components, and understand electronics theory. "
            "Be concise, technical, and accurate. Always prioritize safety and best practices."
        )
    }
    
    # Prepend system prompt if not already present
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, system_prompt)

    response_text = await ai_service.get_response(messages)
    return {"content": response_text}
