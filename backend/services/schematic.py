import os
from kicad_sch_api import Schematic, Component
from datetime import datetime

class SchematicService:
    def __init__(self, output_dir: str = "generated_schematics"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _escape_sexp_string(self, value: str) -> str:
        """
        Escapes a string for use in a KiCad S-Expression.
        Escapes backslashes and quotes.
        """
        if not value:
            return ""
        # Escape backslashes first, then quotes
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def generate_single_component_sch(self, mpn: str, supplier_id: str) -> str:
        """
        Generates a KiCad 9 schematic with an embedded symbol for the component.
        """
        # Create a basic rectangular symbol definition
        symbol_uuid = "00000000-0000-0000-0000-000000000001"

        # Sanitize inputs for S-Expression injection
        safe_mpn = self._escape_sexp_string(mpn)
        lib_symbol_name = f"{safe_mpn}_Lib"
        
        # KiCad 9 S-Expression for a simple box symbol
        # This is a raw string injection because kicad-sch-api might not support full embedded symbol creation yet.
        # We will use the library to create the base, then inject the symbol if needed, 
        # OR just use a text label if the symbol is too complex.
        
        # Better approach for MVP: Create the schematic object and add a text note + a simple unplaced symbol instance.
        sch = Schematic()
        # Note: sch.title isn't used in the manual string construction below, but good to keep for future.
        sch.title = f"Component: {mpn}"
        sch.date = datetime.now().strftime("%Y-%m-%d")

        # Note: kicad_sch_api usually requires a Symbol object to add a component.
        # Since we don't have a library table set up on the server, we cannot easily "place" a verified symbol.
        # However, we can create a "Project Library" embedded.
        
        # For this specific MVP fix, let's manually write a valid KiCad 9 file with one embedded symbol
        # because the API library might be limited in generating *embedded* symbols without a source lib.
        
        filename = f"{mpn}_{supplier_id}.kicad_sch".replace("/", "_").replace("\\", "_")
        file_path = os.path.join(self.output_dir, filename)
        
        # Manual construction of a minimal valid KiCad 9 schematic with one symbol
        file_content = f"""(kicad_sch
    (version 20250114)
    (generator "TripleT-Agent")
    (uuid "33694086-6638-4672-8418-1850388e3609")
    (paper "A4")
    (lib_symbols
      (symbol "{lib_symbol_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
        (property "Reference" "U" (at 0 7.62 0)
          (effects (font (size 1.27 1.27)))
        )
        (property "Value" "{safe_mpn}" (at 0 5.08 0)
          (effects (font (size 1.27 1.27)))
        )
        (property "Footprint" "" (at 0 -7.62 0)
          (effects (font (size 1.27 1.27)) hide)
        )
        (symbol "{lib_symbol_name}_1_1"
          (rectangle (start -5.08 3.81) (end 5.08 -3.81)
            (stroke (width 0.254) (type default))
            (fill (type background))
          )
        )
        (symbol "{lib_symbol_name}_1_1"
          (pin input line (at -7.62 0 0) (length 2.54)
            (name "Pin1" (effects (font (size 1.27 1.27))))
            (number "1" (effects (font (size 1.27 1.27))))
          )
        )
      )
    )
    (symbol (lib_id "{lib_symbol_name}") (at 100 100 0) (unit 1)
      (in_bom yes) (on_board yes) (dnp no)
      (uuid "{symbol_uuid}")
      (property "Reference" "U1" (at 100 92.38 0))
      (property "Value" "{safe_mpn}" (at 100 94.92 0))
    )
    (sheet_instances
      (path "/" (page "1"))
    )
)"""
        
        with open(file_path, "w") as f:
            f.write(file_content)
            
        return file_path

schematic_service = SchematicService()
