"""Adapter JDIH Kemenkeu — SSR (Next.js) + flight data JSON.

Daftar: div.jdih-search (10 item/halaman, ?page=N).
PDF: full_text_pdf ada di flight data `self.__next_f` pada halaman daftar.
"""
import json
import re
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import clean_text, parse_id_date, soup


class KemenkeuAdapter(BaseAdapter):
    key = "kemenkeu"
    nama = "Kemenkeu"
    base_url = "https://jdih.kemenkeu.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        out = []
        seen = set()
        for page in range(1, 12):  # batas aman 11 halaman
            url = self.listing_url if page == 1 else self._with_page(page)
            resp = await self.http.get(url)
            if resp.status_code != 200:
                break
            html = resp.text
            s = soup(html)
            cards = s.select("div.jdih-search")
            if not cards:
                break
            # flight data: full_text_pdf muncul dengan quote ter-escape (\\"),
            # urutannya sejajar dengan urutan kartu di halaman.
            pdfs = re.findall(r'\\?"full_text_pdf\\?"\s*:\\s*\\?"(/api/download/[^\\"]+)', html)
            new_items = 0
            for idx, c in enumerate(cards):
                a = c.select_one("h5.item a")
                if not a:
                    continue
                nomor = clean_text(a.get_text(" ", strip=True))
                judul = clean_text(c.select_one("p.item").get_text(" ", strip=True)) if c.select_one("p.item") else ""
                tgl = None
                metas = [clean_text(li.get_text(" ", strip=True)) for li in c.select("ul.search-meta.item li")]
                for m in metas:
                    if "Ditetapkan" in m:
                        tgl = parse_id_date(m)
                        break
                if tgl and tgl < since:
                    continue
                if nomor in seen:
                    continue
                seen.add(nomor)
                slug = a.get("href", "")
                detail = self.abs_url(slug)
                pdf = pdfs[idx] if idx < len(pdfs) else None
                out.append(RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=nomor,
                    judul=judul,
                    tanggal=tgl,
                    url_detail=detail,
                    url_pdf=self.abs_url(pdf) if pdf else None,
                    extra={"meta": metas},
                ))
                new_items += 1
            # stop kalau halaman ini tidak menghasilkan item baru (lewat rentang)
            if new_items == 0 and len(cards) > 0:
                break
        return out

    def _with_page(self, page: int) -> str:
        sep = "&" if "?" in self.listing_url else "?"
        return re.sub(r"page=\d+", f"page={page}", self.listing_url) or f"{self.listing_url}{sep}page={page}"
