"""Parsing dokumen: Mistral OCR bila key tersedia, fallback pypdf bila tidak."""
import io

from pypdf import PdfReader

from app.config import get_settings

settings = get_settings()


async def parse_pdf(pdf_bytes: bytes) -> str:
    """Ekstrak teks dari PDF.

    - Bila MISTRAL_API_KEY diisi: gunakan Mistral OCR (bagus untuk PDF scan).
    - Bila kosong: fallback pypdf (hanya untuk PDF berbasis teks).
    """
    if settings.mistral_api_key:
        try:
            return await _mistral_ocr(pdf_bytes)
        except Exception:
            # fallback ke pypdf kalau Mistral gagal
            pass
    return _pypdf_text(pdf_bytes)


async def _mistral_ocr(pdf_bytes: bytes) -> str:
    import httpx

    url = "https://api.mistral.ai/v1/files"
    headers = {"Authorization": f"Bearer {settings.mistral_api_key}"}
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            url,
            headers=headers,
            files={"file": ("dokumen.pdf", pdf_bytes, "application/pdf")},
        )
        resp.raise_for_status()
        file_id = resp.json()["id"]
        # dapatkan URL unduh
        resp2 = await client.get(f"{url}/{file_id}/url", headers=headers)
        resp2.raise_for_status()
        file_url = resp2.json()["url"]
        # OCR
        resp3 = await client.post(
            "https://api.mistral.ai/v1/ocr",
            headers=headers,
            json={"model": settings.mistral_model, "document": {"type": "document_url", "document_url": file_url}},
        )
        resp3.raise_for_status()
        data = resp3.json()
        pages = data.get("pages", [])
        return "\n\n".join(p.get("markdown", "") for p in pages)


def _pypdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts)
    if len(text.strip()) < 50:
        raise RuntimeError(
            "PDF tampaknya hasil scan (tidak ada teks). "
            "Isi MISTRAL_API_KEY di halaman /admin > Konfigurasi untuk OCR."
        )
    return text
