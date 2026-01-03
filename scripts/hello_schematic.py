import kicad_sch_api as ksa
from kicad_sch_api import Schematic

def create_hello_world():
    # Initialize a new schematic
    sch = Schematic()
    
    # We can try to set metadata directly if supported
    # Inspecting Schematic object might be needed if title/date aren't direct attributes
    # But let's try assuming they are or just saving a blank one first.
    
    # sch.title = "TripleT Agent Hello World" # Commenting out uncertain attributes for now
    
    # Save the file
    output_path = "hello_world.kicad_sch"
    sch.save(output_path)
    print(f"Generated {output_path}")

if __name__ == "__main__":
    create_hello_world()
