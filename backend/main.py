from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.services.lcsc import lcsc_service, Part
from typing import List

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
