"""Adapter JDIH Kemendag — SSR, kartu tanpa tanggal (tanggal di detail).

Kartu: div.card.peraturan-card. Link detail di h6 a. Tanggal & PDF perlu buka detail.
Untuk hemat request, kita ambil detail hanya untuk item yang tanggalnya tidak diketahui
oleh pipeline (crawl service akan memanggil enrich bila perlu).
"""
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import clean_text, parse_id_date, soup


class KemendagAdapter(BaseAdapter):
    key = "kemendag"
    nama = "Kemendag"
    base_url = "https://jdih.kemendag.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        out = []
        seen = set()
        for page in range(1, 8):  # batas aman
            url = self.listing_url if page == 1 else self._with_page(page)
            resp = await self.http.get(url)
            if resp.status_code != 200:
                break
            s = soup(resp.text)
            cards = s.select("div.card.peraturan-card")
            if not cards:
                break
            for c in cards:
                a = c.select_one("h6 a")
                if not a:
                    continue
                nomor = clean_text(a.get_text(" ", strip=True))
                if nomor in seen:
                    continue
                seen.add(nomor)
                judul = clean_text(c.select_one("p.text-muted").get_text(" ", strip=True)) if c.select_one("p.text-muted") else ""
                detail = self.abs_url(a.get("href", ""))
                out.append(RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=nomor,
                    judul=judul,
                    tanggal=None,
                    url_detail=detail,
                    url_pdf=None,
                ))
        return out

    async def enrich(self, raw: RawRegulation) -> RawRegulation:
        """Buka halaman detail untuk ambil tanggal & PDF."""
        if not raw.url_detail:
            return raw
        resp = await self.http.get(raw.url_detail)
        if resp.status_code != 200:
            return raw
        s = soup(resp.text)
        # tanggal: cari teks "Ditetapkan" / "Tanggal"
        tgl = None
        for node in s.find_all(string=lambda t: t and "Ditetapkan" in t):
            tgl = parse_id_date(node.strip())
            if tgl:
                break
        if tgl is None:
            for node in s.find_all("td", string=lambda t: t and "Tanggal" in str(t)):
                tgl = parse_id_date(node.get_text(" ", strip=True))
                if tgl:
                    break
        raw.tanggal = tgl
        # PDF
        pdf = None
        iframe = s.select_one("iframe[src*='.pdf']")
        if iframe:
            pdf = iframe.get("src")
        if not pdf:
            for a in s.select("a[href*='.pdf']"):
                href = a.get("href", "")
                if href and "download" in href.lower():
                    pdf = href
                    break
        if not pdf:
            a = s.select_one("a[href*='peraturan/download']")
            if a:
                pdf = a.get("href")
        if pdf:
            raw.url_pdf = self.abs_url(pdf)
        return raw

    def _with_page(self, page: int) -> str:
        sep = "&" if "?" in self.listing_url else "?"
        import re
        if re.search(r"page=\d+", self.listing_url):
            return re.sub(r"page=\d+", f"page={page}", self.listing_url)
        return f"{self.listing_url}{sep}page={page}"
