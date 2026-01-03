from fastapi import FastAPI

app = FastAPI(title="TripleT KiCad Agent")

@app.get("/")
def read_root():
    return {"message": "Welcome to TripleT KiCad Agent API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
