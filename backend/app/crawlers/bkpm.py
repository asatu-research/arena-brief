"""Adapter JDIH BKPM — JSON API publik, tanpa render.

Endpoint: GET /api/document-search?... (path dari listing URL, ganti /id/search -> /api/document-search)
"""
from datetime import date
from urllib.parse import urlsplit, urlunsplit

from app.crawlers.base import BaseAdapter, RawRegulation


class BkpmAdapter(BaseAdapter):
    key = "bkpm"
    nama = "Kemeninves / BKPM"
    base_url = "https://jdih.bkpm.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        parts = urlsplit(self.listing_url)
        path = parts.path.replace("/id/search", "/api/document-search")
        api_url = urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))
        resp = await self.http.get(api_url)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("allDocuments", [])
        out = []
        for it in items:
            tgl = (it.get("establishment_date") or it.get("publication_date") or "")[:10]
            try:
                t = date.fromisoformat(tgl) if tgl else None
            except ValueError:
                t = None
            if t and t < since:
                continue
            nomor = it.get("regulation_number") or ""
            tahun = it.get("regulation_year") or 0
            if not tahun and t:
                tahun = t.year
            judul = it.get("title") or ""
            out.append(
                RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=f"{nomor} Tahun {tahun}".strip() if nomor and tahun else judul,
                    judul=judul,
                    tanggal=t,
                    url_detail=self.abs_url(f"/id/document/{it.get('slug','')}") if it.get("slug") else None,
                    url_pdf=it.get("document_file_url"),
                    extra={"status": it.get("status_latest") or it.get("status") or ""},
                )
            )
        return out
