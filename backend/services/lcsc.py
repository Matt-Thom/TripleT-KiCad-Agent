import json
import logging

import httpx
from pydantic import BaseModel, Field
from typing import List, Optional

logger = logging.getLogger(__name__)

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

    # Keys under which upstream responses expose a datasheet link. The
    # `full=true` rows use `datasheet`; the rest are defensive aliases.
    _DATASHEET_KEYS = ("datasheet", "datasheet_url", "datasheetUrl")

    @classmethod
    def _extract_datasheet_url(cls, item: dict) -> Optional[str]:
        for key in cls._DATASHEET_KEYS:
            value = item.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value
        return None

    @staticmethod
    def _extract_price(raw: object) -> float:
        """Normalize price across response shapes.

        The compact response carries a plain number; `full=true` rows carry the
        raw JLC price column: a JSON array of quantity tiers like
        `[{"qFrom": 1, "qTo": 9, "price": 0.0148}, ...]` — take the first tier.
        """
        if raw is None:
            return 0.0
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            try:
                return float(raw)
            except ValueError:
                pass
            try:
                tiers = json.loads(raw)
                if isinstance(tiers, list) and tiers and isinstance(tiers[0], dict):
                    return float(tiers[0].get("price", 0.0))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return 0.0

    @staticmethod
    def _format_lcsc_id(raw: object) -> str:
        """LCSC part numbers are conventionally 'C'-prefixed (e.g. C8734)."""
        lcsc_id = str(raw or "").strip()
        if lcsc_id and not lcsc_id.upper().startswith("C"):
            lcsc_id = f"C{lcsc_id}"
        return lcsc_id

    async def search(self, keyword: str) -> List[Part]:
        async with httpx.AsyncClient() as client:
            try:
                # full=true returns the raw component rows, which include the
                # datasheet URL that the compact response omits.
                response = await client.get(
                    self.BASE_URL,
                    params={"q": keyword, "full": "true", "limit": "10"},
                    headers={"User-Agent": "TripleT-KiCad-Agent/0.1"}
                )
                if response.status_code >= 500:
                    return [] # Return empty list but log internally, or we could raise.

                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("components", []):
                    # Map API response to our unified Part model
                    part = Part(
                        mpn=item.get("mfr", "Unknown"),
                        manufacturer=item.get("manufacturer") or "Unknown",
                        description=item.get("description", ""),
                        price=self._extract_price(item.get("price")),
                        stock=int(item.get("stock", 0) or 0),
                        supplier_part_number=self._format_lcsc_id(item.get("lcsc", "")),
                        supplier="LCSC",
                        datasheet_url=self._extract_datasheet_url(item),
                        attributes={
                            "Package": item.get("package", ""),
                            "Basic": bool(item.get("is_basic", item.get("basic", False))),
                            "Preferred": bool(item.get("is_preferred", item.get("preferred", False)))
                        }
                    )
                    results.append(part)
                return results

            except Exception as e:
                logger.warning(f"LCSC Search Error: {e}")
                return []

lcsc_service = LCSCService()
