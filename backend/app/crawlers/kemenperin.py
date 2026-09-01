"""Adapter JDIH Kemenperin & ESDM — SSR Yii2, struktur identik (.list-view > .item).

Daftar: judul di `p > a.text-primary` (href /dokumen/view?id=...), PDF langsung di daftar
(`a.text-theme-color`, href /common/dokumen/... atau /dokumen/download?id=...).
Tanggal tidak ada di daftar; hanya tahun. Pipeline akan enrich bila perlu.
"""
import re
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import clean_text, parse_id_date, soup


class KemenperinAdapter(BaseAdapter):
    key = "kemenperin"
    nama = "Kemenperin"
    base_url = "https://jdih.kemenperin.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        return await self._fetch_list(since, pdf_pattern="/common/dokumen/")

    async def enrich(self, raw: RawRegulation) -> RawRegulation:
        return await self._enrich_detail(raw)

    async def _fetch_list(self, since: date, pdf_pattern: str) -> list[RawRegulation]:
        out = []
        seen = set()
        for page in range(1, 12):
            url = self._with_page(page)
            resp = await self.http.get(url)
            if resp.status_code != 200:
                break
            s = soup(resp.text)
            items = s.select(".list-view > .item")
            if not items:
                break
            for it in items:
                a = it.select_one("p > a.text-primary")
                if not a:
                    continue
                judul = clean_text(a.get_text(" ", strip=True))
                m = re.search(r"Nomor\s+(\d+)\s+Tahun\s+(\d{4})", judul)
                nomor = f"{m.group(1)} Tahun {m.group(2)}" if m else judul
                if nomor in seen:
                    continue
                seen.add(nomor)
                pdf_a = it.select_one("a.text-theme-color")
                pdf = pdf_a.get("href") if pdf_a else None
                if pdf and pdf_pattern and pdf_pattern not in pdf and pdf != "#":
                    pdf = None
                detail = self.abs_url(a.get("href"))
                out.append(RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=nomor,
                    judul=judul,
                    tanggal=None,
                    url_detail=detail,
                    url_pdf=self.abs_url(pdf) if pdf else None,
                ))
        return out

    async def _enrich_detail(self, raw: RawRegulation) -> RawRegulation:
        if raw.tanggal or not raw.url_detail:
            return raw
        resp = await self.http.get(raw.url_detail)
        if resp.status_code != 200:
            return raw
        s = soup(resp.text)
        tgl = None
        for node in s.find_all(string=lambda t: t and ("Ditetapkan" in t or "Tanggal" in t)):
            tgl = parse_id_date(node.strip())
            if tgl:
                break
        raw.tanggal = tgl
        return raw

    def _with_page(self, page: int) -> str:
        sep = "&" if "?" in self.listing_url else "?"
        if re.search(r"page=\d+", self.listing_url):
            return re.sub(r"page=\d+", f"page={page}", self.listing_url)
        return f"{self.listing_url}{sep}page={page}"


class EsdmAdapter(KemenperinAdapter):
    key = "esdm"
    nama = "Kemen ESDM"
    base_url = "https://jdih.esdm.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        # ESDM pakai /dokumen/download?id=... (controller), bukan path statis
        return await self._fetch_list(since, pdf_pattern="")
