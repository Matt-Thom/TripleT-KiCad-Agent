# Component Search Strategy

## 1. Primary Sources

### LCSC (via JLCPCB)
*   **Why:** Best for "Maker" / "Hobbyist" pricing and direct integration with JLCPCB assembly.
*   **Access Method:** 
    *   **Official API:** Requires application and approval (can be slow).
    *   **Alternative:** `jlcparts` / `jlcsearch` (Community tools/APIs).
    *   **Recommendation:** Start with `jlcsearch` (unofficial) for rapid prototyping, move to Official API if volume grows.

### DigiKey
*   **Why:** The industry standard for availability and comprehensive parametric data.
*   **Access Method:** Official API (V3).
*   **Requirement:** OAuth2 App Registration (Client ID + Secret).
*   **Status:** Needs credentials from the user.

### Mouser
*   **Why:** Good backup to DigiKey.
*   **Access Method:** Search API.
*   **Requirement:** API Key.

## 2. Implementation Plan

### Phase 1: The "Easy" Path (LCSC)
We will implement a search function using `jlcsearch` (or equivalent) because it requires no authentication to start.

### Phase 2: The "Pro" Path (DigiKey)
We will add a "Settings" page in the Web UI where the user can input their DigiKey Client ID/Secret.

## 3. Data Normalization
We need a unified `Part` model in Python:
```python
class Part:
    mpn: str  # Manufacturer Part Number
    manufacturer: str
    description: str
    price: float
    stock: int
    datasheet_url: str
    supplier: str # "LCSC", "DigiKey"
    attributes: dict # {"Voltage": "5V", "Package": "0603"}
```
