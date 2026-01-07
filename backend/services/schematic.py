import os
import re
from kicad_sch_api import Schematic, Component
from datetime import datetime

class SchematicService:
    def __init__(self, output_dir: str = "generated_schematics"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize input to be safe for filenames.
        Allows alphanumeric, underscore, hyphen, and dot.
        Replaces everything else with underscore.
        """
        # Replace directory separators and common unsafe chars
        safe_name = re.sub(r'[^\w\-\.]', '_', name)
        # Prevent traversal (though the regex handles / and \)
        return safe_name

    def escape_sexp_string(self, value: str) -> str:
        """
        Escape a string for use in a KiCad S-Expression.
        KiCad uses double quotes for strings. We need to escape double quotes and backslashes.
        """
        if not value:
            return ""
        # Escape backslashes first, then quotes
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return escaped

    def generate_single_component_sch(self, mpn: str, supplier_id: str) -> str:
        """
        Generates a KiCad 9 schematic with an embedded symbol for the component.
        """
        # Sanitize inputs
        safe_mpn_filename = self.sanitize_filename(mpn)
        safe_supplier_id = self.sanitize_filename(supplier_id)
        
        # Escape inputs for S-Expression content
        # Note: We use the original mpn for the display value, but safely escaped
        escaped_mpn = self.escape_sexp_string(mpn)
        
        # For the internal library symbol name, use a safe version to avoid syntax errors
        # if mpn contains spaces or special chars that might confuse the parser even if quoted
        safe_lib_symbol_name = self.escape_sexp_string(f"{safe_mpn_filename}_Lib")

        # Create a basic rectangular symbol definition
        symbol_uuid = "00000000-0000-0000-0000-000000000001"
        
        filename = f"{safe_mpn_filename}_{safe_supplier_id}.kicad_sch"
        file_path = os.path.join(self.output_dir, filename)
        
        # Manual construction of a minimal valid KiCad 9 schematic with one symbol
        # WE use safe_lib_symbol_name for identifiers and escaped_mpn for the Value property
        file_content = f"""(kicad_sch
    (version 20250114)
    (generator "TripleT-Agent")
    (uuid "33694086-6638-4672-8418-1850388e3609")
    (paper "A4")
    (lib_symbols
      (symbol "{safe_lib_symbol_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
        (property "Reference" "U" (at 0 7.62 0)
          (effects (font (size 1.27 1.27)))
        )
        (property "Value" "{escaped_mpn}" (at 0 5.08 0)
          (effects (font (size 1.27 1.27)))
        )
        (property "Footprint" "" (at 0 -7.62 0)
          (effects (font (size 1.27 1.27)) hide)
        )
        (symbol "{safe_lib_symbol_name}_1_1"
          (rectangle (start -5.08 3.81) (end 5.08 -3.81)
            (stroke (width 0.254) (type default))
            (fill (type background))
          )
        )
        (symbol "{safe_lib_symbol_name}_1_1"
          (pin input line (at -7.62 0 0) (length 2.54)
            (name "Pin1" (effects (font (size 1.27 1.27))))
            (number "1" (effects (font (size 1.27 1.27))))
          )
        )
      )
    )
    (symbol (lib_id "{safe_lib_symbol_name}") (at 100 100 0) (unit 1)
      (in_bom yes) (on_board yes) (dnp no)
      (uuid "{symbol_uuid}")
      (property "Reference" "U1" (at 100 92.38 0))
      (property "Value" "{escaped_mpn}" (at 100 94.92 0))
    )
    (sheet_instances
      (path "/" (page "1"))
    )
)"""
        
        with open(file_path, "w") as f:
            f.write(file_content)
            
        return file_path

schematic_service = SchematicService()
