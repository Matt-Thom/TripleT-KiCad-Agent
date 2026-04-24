"""Datasheet fetching and PDF text extraction.

Thin wrapper over httpx + pdfplumber. All failure modes (HTTP errors, non-PDF
responses, parse errors) are surfaced as `DatasheetError` so callers can handle
them uniformly.
"""
from __future__ import annotations

import io
import logging

import httpx
import pdfplumber

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF-"
_FETCH_TIMEOUT_S = 30.0


class DatasheetError(Exception):
    """Raised when a datasheet cannot be fetched or its text extracted."""


def extract_text_from_pdf_bytes(data: bytes) -> str:
    if not data.startswith(_PDF_MAGIC):
        raise DatasheetError("Response does not look like a PDF (missing %PDF- header).")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as e:
        raise DatasheetError(f"Failed to parse PDF: {e}") from e
    return "\n".join(pages)


async def extract_datasheet_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_S, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content
    except httpx.HTTPError as e:
        raise DatasheetError(f"Failed to fetch datasheet from {url}: {e}") from e
    return extract_text_from_pdf_bytes(content)
