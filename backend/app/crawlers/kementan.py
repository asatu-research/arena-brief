"""Adapter JDIH Kementan — Next.js CSR + API publik dengan Bearer token (ditemukan di bundle).

Endpoint: GET {base}/jdih-ops/api/peraturan?page=N&per_page=8&tahun=2026&...
Token bisa berubah saat redeploy; fallback: render Playwright ke /peraturan.
"""
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import parse_id_date

API_BASE = "https://jdih.pertanian.go.id/jdih-ops"
BEARER = "1|NVPf4scT4EurUpxadlrdYoPxpEeb6kjYDsCnL9aVea52f653"


class KementanAdapter(BaseAdapter):
    key = "kementan"
    nama = "Kementan"
    base_url = "https://jdih.pertanian.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        items = await self._fetch_api(since)
        if items is None:
            items = await self._fetch_browser(since)
        return items

    async def _fetch_api(self, since: date):
        out = []
        page = 1
        while page <= 12:
            # keyword memaksa hasil berisi frasa "Peraturan Menteri"; jenis untuk Permen Pertanian = "permentan"
            url = f"{API_BASE}/api/peraturan?page={page}&per_page=50&keyword=Peraturan%20Menteri"
            resp = await self.http.get(url, headers={"Authorization": f"Bearer {BEARER}", "Accept": "application/json"})
            if resp.status_code != 200:
                return None
            try:
                data = resp.json()
            except Exception:
                return None
            rows = (data.get("data") or {}).get("data") or []
            if not rows:
                break
            for it in rows:
                judul = it.get("judul") or ""
                if not judul.lower().startswith("peraturan menteri"):
                    continue
                tgl = parse_id_date(it.get("ditetapkan") or "")
                if tgl and tgl < since:
                    continue
                slug = it.get("slug") or ""
                out.append(RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=f"{it.get('nomor','')} Tahun {it.get('tahun','')}",
                    judul=judul,
                    tanggal=tgl,
                    url_detail=self.abs_url(f"/peraturan/{slug}") if slug else None,
                    url_pdf=None,
                    extra={"status": it.get("status") or "", "slug": slug},
                ))
            page += 1
        return out

    async def _fetch_browser(self, since: date):
        out = []
        if self._browser is None:
            return out
        html = await self._browser.html(
            "https://jdih.pertanian.go.id/peraturan",
            wait_selector="a[href^='/peraturan/']",
        )
        from app.crawlers.utils import soup, clean_text
        s = soup(html)
        for a in s.select("a[href^='/peraturan/']"):
            card = a.select_one("h3") or a
            judul = clean_text(card.get_text(" ", strip=True))
            if not judul.lower().startswith("peraturan menteri"):
                continue
            # tanggal tersembunyi di dalam kartu
            tgl_txt = ""
            spans = a.select("span")
            for sp in spans:
                if "Ditetapkan" in sp.get_text():
                    tgl_txt = sp.get_text()
                    break
            tgl = parse_id_date(tgl_txt)
            if tgl and tgl < since:
                continue
            slug = a.get("href", "").strip("/").split("/")[-1]
            out.append(RawRegulation(
                jenis="Peraturan Menteri",
                nomor=slug,
                judul=judul,
                tanggal=tgl,
                url_detail=self.abs_url(a.get("href")),
                url_pdf=None,
            ))
        return out
