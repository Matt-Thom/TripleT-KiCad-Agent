from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.services.lcsc import lcsc_service, Part
from backend.services.schematic import schematic_service
from typing import List
import os

app = FastAPI(title="TripleT KiCad Agent")

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
