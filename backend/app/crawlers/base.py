"""Base untuk adapter crawler JDIH."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import httpx


@dataclass
class RawRegulation:
    jenis: str
    nomor: str
    judul: str
    tanggal: Optional[date] = None
    url_detail: Optional[str] = None
    url_pdf: Optional[str] = None
    extra: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """Adapter satu situs JDIH.

    `fetch` dipanggil dengan client HTTP yang sudah punya UA browser.
    Bila situs butuh render JS, gunakan engine Playwright yang tersedia
    melalui `_browser` (di-set oleh crawl service bila tersedia).
    """

    key: str = ""
    nama: str = ""
    base_url: str = ""

    def __init__(self, listing_url: str, http: httpx.AsyncClient, browser=None):
        self.listing_url = listing_url
        self.http = http
        self._browser = browser

    @abstractmethod
    async def fetch(self, since: date) -> list[RawRegulation]:
        ...

    def abs_url(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("http"):
            return url
        base = self.base_url.rstrip("/")
        if url.startswith("/"):
            return base + url
        return base + "/" + url
