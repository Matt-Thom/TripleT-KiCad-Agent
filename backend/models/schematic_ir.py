from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from backend.services.procedural_symbol import PinSpec

# --- Logical Block Diagram Schemas ---
class LogicalBlock(BaseModel):
    id: str = Field(..., description="Unique ID of the block, e.g. 'mcu', 'ldo'")
    type: str = Field(..., description="Block type, e.g. 'MCU', 'Regulator', 'Sensor', 'Connector'")
    description: str = Field("", description="Functional description and constraints")
    voltage_domain: str = Field("3.3V", description="Operating voltage domain, e.g., 3.3V, 5V, Vbat")

class BlockConnection(BaseModel):
    source_block_id: str
    target_block_id: str
    type: str = Field("Power", description="Connection type, e.g., I2C, SPI, Power, GPIO")
    description: str = ""

class BlockDiagramData(BaseModel):
    blocks: List[LogicalBlock] = Field(default_factory=list)
    connections: List[BlockConnection] = Field(default_factory=list)

# --- Structural Schematic IR Schemas ---
class PinRef(BaseModel):
    component_ref: str = Field(..., description="E.g., 'U1'")
    pin_number: str = Field(..., description="E.g., '12'")

class NetConnection(BaseModel):
    name: str = Field(..., description="E.g., 'GND', '3V3', 'I2C_SDA'")
    connections: List[PinRef] = Field(default_factory=list)

class ComponentInstance(BaseModel):
    reference: str = Field(..., description="Unique designator, e.g. 'U1', 'C1'")
    mpn: str = Field(..., description="Manufacturer Part Number")
    supplier_id: str = Field(..., description="LCSC Part Number")
    value: str = Field("", description="Component value or variant name")
    pins: List[PinSpec] = Field(default_factory=list)
    block_id: Optional[str] = Field(None, description="Logical block ID this component maps to")
    properties: Dict[str, str] = Field(default_factory=dict)

class SchematicIRData(BaseModel):
    components: List[ComponentInstance] = Field(default_factory=list)
    nets: List[NetConnection] = Field(default_factory=list)
