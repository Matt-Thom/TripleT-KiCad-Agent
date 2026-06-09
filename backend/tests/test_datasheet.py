"""Tests for backend.services.datasheet — PDF text extraction."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_tiny_pdf(text: str) -> bytes:
    """Build a minimal valid PDF whose single page contains `text` (ASCII only).

    Hermetic: avoids pulling in reportlab/fpdf just to produce a fixture.
    """
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def test_extract_text_from_pdf_bytes_returns_page_text():
    from backend.services.datasheet import extract_text_from_pdf_bytes

    pdf = _make_tiny_pdf("Pin 1: VCC supply input")

    result = extract_text_from_pdf_bytes(pdf)

    assert "Pin 1: VCC" in result


def test_extract_text_from_pdf_bytes_raises_on_non_pdf():
    from backend.services.datasheet import DatasheetError, extract_text_from_pdf_bytes

    with pytest.raises(DatasheetError):
        extract_text_from_pdf_bytes(b"this is not a pdf")


@pytest.mark.asyncio
async def test_extract_datasheet_text_fetches_and_parses():
    from backend.services import datasheet as ds_mod
    from backend.services.datasheet import extract_datasheet_text

    pdf_bytes = _make_tiny_pdf("Datasheet content: Pin 8 GND")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = pdf_bytes
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch.object(ds_mod.httpx, "AsyncClient", return_value=mock_client):
        text = await extract_datasheet_text("https://example.com/ds.pdf")

    assert "Pin 8 GND" in text
    mock_client.get.assert_awaited_once()
    called_url = mock_client.get.await_args.args[0]
    assert called_url == "https://example.com/ds.pdf"


@pytest.mark.asyncio
async def test_extract_datasheet_text_raises_on_http_error():
    import httpx

    from backend.services import datasheet as ds_mod
    from backend.services.datasheet import DatasheetError, extract_datasheet_text

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock(status_code=404)
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch.object(ds_mod.httpx, "AsyncClient", return_value=mock_client):
        with pytest.raises(DatasheetError):
            await extract_datasheet_text("https://example.com/missing.pdf")


@pytest.mark.asyncio
async def test_extract_datasheet_text_raises_on_non_pdf_response():
    from backend.services import datasheet as ds_mod
    from backend.services.datasheet import DatasheetError, extract_datasheet_text

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"<html>not a pdf</html>"
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch.object(ds_mod.httpx, "AsyncClient", return_value=mock_client):
        with pytest.raises(DatasheetError):
            await extract_datasheet_text("https://example.com/bad.pdf")
