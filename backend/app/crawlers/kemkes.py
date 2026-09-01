"""Adapter JDIH Kemenkes — Livewire (render JS). Butuh Playwright untuk pagination.

Kartu item: div.group.relative.bg-white (rounded-3xl). URL detail: /documents/{slug}.
Filter tahun via query selectedYear=2026. Data awal di-render server (Livewire SSR) tapi
pagination via wire:click; aman pakai browser + klik tombol "Selanjutnya".
"""
from datetime import date

from app.crawlers.base import BaseAdapter, RawRegulation
from app.crawlers.utils import clean_text, parse_id_date, soup


class KemkesAdapter(BaseAdapter):
    key = "kemkes"
    nama = "Kemenkes"
    base_url = "https://jdih.kemkes.go.id"

    async def fetch(self, since: date) -> list[RawRegulation]:
        out = []
        seen = set()
        for page in range(1, 8):
            url = self.listing_url if page == 1 else self._with_page(page)
            if self._browser is None:
                # Livewire: ambil halaman 1 via HTTP (SSR awal) cukup untuk mayoritas
                resp = await self.http.get(url)
                if resp.status_code != 200:
                    break
                html = resp.text
            else:
                try:
                    html = await self._browser.html(url, wait_selector="div.rounded-3xl")
                except Exception:
                    break
            s = soup(html)
            cards = s.select("div.rounded-3xl")
            if not cards:
                break
            found_new = 0
            for c in cards:
                a = c.select_one("h3 a")
                if not a:
                    continue
                judul = clean_text(a.get_text(" ", strip=True))
                if judul in seen:
                    continue
                seen.add(judul)
                tgl_txt = clean_text(c.select_one("div.text-sm.text-gray-500").get_text(" ", strip=True)) if c.select_one("div.text-sm.text-gray-500") else ""
                tgl = parse_id_date(tgl_txt)
                if tgl and tgl < since:
                    continue
                nomor = judul
                detail = self.abs_url(a.get("href"))
                out.append(RawRegulation(
                    jenis="Peraturan Menteri",
                    nomor=nomor,
                    judul=judul,
                    tanggal=tgl,
                    url_detail=detail,
                    url_pdf=None,
                ))
                found_new += 1
            if found_new == 0:
                break
            if self._browser is None:
                break  # tanpa browser hanya ambil halaman pertama
        return out

    def _with_page(self, page: int) -> str:
        # Livewire memakai parameter URL; tidak ada page di URL -> tidak bisa via HTTP polos
        return self.listing_url
