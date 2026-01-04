from fastapi import APIRouter, HTTPException
from backend.models.settings import Settings
import os

router = APIRouter()

# In-memory storage for MVP. In production, use a database or write to .env
# Note: Writing to .env at runtime is tricky. We'll use os.environ for the session.
# For persistence, we should consider a local sqlite db or json file later.
SETTINGS_FILE = ".env" 

def load_settings():
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        default_model=os.getenv("DEFAULT_AI_MODEL", "gemini/gemini-pro"),
        kicad_symbol_dir=os.getenv("KICAD_SYMBOL_DIR", ""),
        kicad_footprint_dir=os.getenv("KICAD_FOOTPRINT_DIR", "")
    )

@router.get("/settings", response_model=Settings)
def get_settings():
    return load_settings()

@router.post("/settings")
def update_settings(settings: Settings):
    # Security: Validate inputs to prevent .env injection
    for field, value in settings.model_dump().items():
        if isinstance(value, str) and value:
            if "\n" in value or "\r" in value:
                raise HTTPException(status_code=400, detail=f"Invalid character (newline) in field {field}")
            if "'" in value:
                raise HTTPException(status_code=400, detail=f"Invalid character (single quote) in field {field}")

    # Update environment variables for the current process
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    if settings.kicad_symbol_dir:
        os.environ["KICAD_SYMBOL_DIR"] = settings.kicad_symbol_dir
    if settings.kicad_footprint_dir:
        os.environ["KICAD_FOOTPRINT_DIR"] = settings.kicad_footprint_dir
    
    os.environ["DEFAULT_AI_MODEL"] = settings.default_model

    # Persist to .env file (Basic implementation)
    try:
        # Quote values to handle spaces and prevent some injection issues,
        # though the newline check above is the primary defense.
        env_content = f"""# AI API Keys
OPENAI_API_KEY='{settings.openai_api_key or ""}'
ANTHROPIC_API_KEY='{settings.anthropic_api_key or ""}'
GEMINI_API_KEY='{settings.gemini_api_key or ""}'
DEFAULT_AI_MODEL='{settings.default_model}'

# KiCad Configuration
KICAD_SYMBOL_DIR='{settings.kicad_symbol_dir or ""}'
KICAD_FOOTPRINT_DIR='{settings.kicad_footprint_dir or ""}'
"""
        with open(SETTINGS_FILE, "w") as f:
            f.write(env_content)
            
    except Exception as e:
        print(f"Failed to save .env: {e}")
        # Non-critical for session, but critical for persistence
    
    return settings
