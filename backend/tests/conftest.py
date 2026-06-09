import os
from pathlib import Path

# Set environment variables for KiCad symbol resolution to point to our test fixtures
fixtures_dir = Path(__file__).parent / "fixtures"
sym_lib_table_path = str(fixtures_dir / "sym-lib-table")

os.environ["KICAD_SYM_LIB_TABLE"] = sym_lib_table_path
os.environ["KICAD7_SYM_LIB_TABLE"] = sym_lib_table_path
os.environ["KICAD8_SYM_LIB_TABLE"] = sym_lib_table_path

os.environ["KICAD_SYMBOL_DIR"] = str(fixtures_dir)
os.environ["KICAD7_SYMBOL_DIR"] = str(fixtures_dir)
os.environ["KICAD8_SYMBOL_DIR"] = str(fixtures_dir)
os.environ["KICAD9_SYMBOL_DIR"] = str(fixtures_dir)
