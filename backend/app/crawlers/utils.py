"""Utility parsing bersama untuk adapter JDIH."""
import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

BULAN_ID = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "agu": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
}
BULAN_ID_FULL = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}


def parse_id_date(text: str) -> Optional[date]:
    """Parse tanggal Indonesia: '24 Agustus 2026', '24 Aug 2026', '15 Jul 2026', '24 April 2026'."""
    if not text:
        return None
    text = text.strip()
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if not m:
        return None
    d, mon, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    if mon in BULAN_ID_FULL:
        mo = BULAN_ID_FULL[mon]
    elif mon[:3] in BULAN_ID:
        mo = BULAN_ID[mon[:3]]
    else:
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()
