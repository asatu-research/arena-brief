"""Adapter JDIH KKP — SSR, seluruh dataset dalam satu halaman (tabel DataTables).

Filter ke Peraturan Menteri KP dilakukan via query param peraturan=52 (kode jenis PermenKP).
PDF tidak ada di daftar; perlu halaman detail (POST PreviewUnduh).
"""
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import clean_text, parse_id_date, soup


class KkpAdapter(BaseAdapter):
    key = "kkp"
    nama = "KKP"
    base_url = "https://jdih.kkp.go.id"

    # kode jenis peraturan di dropdown (peraturan=...). PermenKP = 52 (asumsi; fallback filter teks)
    async def fetch(self, since: date) -> list[RawRegulation]:
        out = []
        for url in (self.listing_url, self.listing_url.split("?")[0] + "?peraturan=52"):
            try:
                resp = await self.http.get(url)
            except Exception:
                continue
            if resp.status_code != 200:
                continue
            s = soup(resp.text)
            rows = s.select("table#example tbody tr")
            if not rows:
                continue
            for tr in rows:
                tds = tr.find_all("td")
                if len(tds) < 7:
                    continue
                jenis = clean_text(tds[1].get_text(" ", strip=True))
                if not jenis.startswith("Peraturan Menteri"):
                    continue
                nomor = clean_text(tds[2].get_text(" ", strip=True))
                a = tds[3].find("a", href=True)
                judul = clean_text(tds[3].get_text(" ", strip=True))
                tgl = parse_id_date(clean_text(tds[4].get_text(" ", strip=True)))
                if tgl and tgl < since:
                    continue
                detail = self.abs_url(a["href"]) if a else None
                out.append(RawRegulation(
                    jenis=jenis,
                    nomor=nomor,
                    judul=judul,
                    tanggal=tgl,
                    url_detail=detail,
                    url_pdf=None,
                    extra={"id": tds[3].find("a", href=True)["href"].rstrip("/").split("/")[-1] if a else ""},
                ))
            return out  # cukup satu sumber yang sukses
        return out
