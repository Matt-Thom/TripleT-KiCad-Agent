from fastapi import FastAPI, HTTPException
from backend.services.lcsc import lcsc_service, Part
from typing import List

app = FastAPI(title="TripleT KiCad Agent")

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
