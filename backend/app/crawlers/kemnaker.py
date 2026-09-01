"""Adapter JDIH Kemnaker — SSR, kartu `.result-card` lengkap dengan tanggal di daftar.

PDF tidak ada di daftar; di halaman detail (kalau ada). Pipeline akan enrich bila url_pdf kosong.
"""
import re
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import clean_text, parse_id_date, soup


class KemnakerAdapter(BaseAdapter):
    key = "kemnaker"
    nama = "Kemnaker"
    base_url = "https://jdih.kemnaker.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        out = []
        seen = set()
        for page in range(1, 12):
            url = self._with_page(page)
            resp = await self.http.get(url)
            if resp.status_code != 200:
                break
            s = soup(resp.text)
            cards = s.select("div.result-card")
            if not cards:
                break
            for c in cards:
                a = c.select_one("h5.title a")
                if not a:
                    continue
                judul = clean_text(a.get_text(" ", strip=True))
                nomor = judul
                if nomor in seen:
                    continue
                seen.add(nomor)
                tgl = None
                info = c.select_one("div.info")
                if info:
                    for div in info.find_all("div"):
                        txt = clean_text(div.get_text(" ", strip=True))
                        if "Ditetapkan" in txt:
                            tgl = parse_id_date(txt)
                            break
                if tgl and tgl < since:
                    continue
                detail = self.abs_url(a.get("href"))
                out.append(RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=nomor,
                    judul=judul,
                    tanggal=tgl,
                    url_detail=detail,
                    url_pdf=None,
                ))
            if not cards:
                break
        return out

    async def enrich(self, raw: RawRegulation) -> RawRegulation:
        if raw.url_pdf or not raw.url_detail:
            return raw
        resp = await self.http.get(raw.url_detail)
        if resp.status_code != 200:
            return raw
        s = soup(resp.text)
        pdf = None
        for a in s.select("a[href*='.pdf'], a[href*='download']"):
            href = a.get("href", "")
            if href and href != "#":
                pdf = href
                break
        if not pdf:
            iframe = s.select_one("iframe[src*='.pdf']")
            if iframe:
                pdf = iframe.get("src")
        if pdf:
            raw.url_pdf = self.abs_url(pdf)
        return raw

    def _with_page(self, page: int) -> str:
        sep = "&" if "?" in self.listing_url else "?"
        if re.search(r"page=\d+", self.listing_url):
            return re.sub(r"page=\d+", f"page={page}", self.listing_url)
        return f"{self.listing_url}{sep}page={page}"
