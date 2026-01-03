import httpx
from pydantic import BaseModel, Field
from typing import List, Optional

class Part(BaseModel):
    mpn: str = Field(..., description="Manufacturer Part Number")
    manufacturer: str = Field("Unknown", description="Manufacturer Name")
    description: str = Field("", description="Part Description")
    price: float = Field(0.0, description="Unit Price (USD)")
    stock: int = Field(0, description="Available Stock")
    supplier_part_number: str = Field(..., description="LCSC Part Number or equivalent")
    supplier: str = Field("LCSC", description="Supplier Name")
    datasheet_url: Optional[str] = None
    attributes: dict = Field(default_factory=dict, description="Parametric data")

class LCSCService:
    BASE_URL = "https://jlcsearch.tscircuit.com/api/search"

    async def search(self, keyword: str) -> List[Part]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.BASE_URL, 
                    params={"q": keyword},
                    headers={"User-Agent": "TripleT-KiCad-Agent/0.1"}
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("components", []):
                    # Map API response to our unified Part model
                    part = Part(
                        mpn=item.get("mfr", "Unknown"),
                        manufacturer="Unknown", # API doesn't seem to return Manufacturer name explicitly in this endpoint
                        description=item.get("description", ""),
                        price=float(item.get("price", 0.0)),
                        stock=int(item.get("stock", 0)),
                        supplier_part_number=str(item.get("lcsc", "")),
                        supplier="LCSC",
                        attributes={
                            "Package": item.get("package", ""),
                            "Basic": item.get("is_basic", False),
                            "Preferred": item.get("is_preferred", False)
                        }
                    )
                    results.append(part)
                return results

            except Exception as e:
                print(f"LCSC Search Error: {e}")
                return []

lcsc_service = LCSCService()
