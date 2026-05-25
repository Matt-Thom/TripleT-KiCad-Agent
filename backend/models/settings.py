from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    default_model: str = "gemini/gemini-pro"
    kicad_symbol_dir: Optional[str] = None
    kicad_footprint_dir: Optional[str] = None
    kicad_sym_lib_table: Optional[str] = None
    port: int = 8080
