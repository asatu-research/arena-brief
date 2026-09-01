"""Pydantic schemas untuk request/response API."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    nama: str
    full_name: str
    adapter: str
    listing_url: str
    aktif: bool
    last_crawl_at: Optional[datetime]
    last_crawl_status: Optional[str]


class SourceIn(BaseModel):
    key: str
    nama: str
    full_name: str
    adapter: str
    listing_url: str
    aktif: bool = True


class RegulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int
    source_key: str = ""
    source_nama: str = ""
    jenis: str
    nomor: str
    judul: str
    tanggal: Optional[date]
    url_detail: Optional[str]
    url_pdf: Optional[str]
    triage_label: Optional[str]
    triage_summary: Optional[str]
    status: str
    ringkas: Optional[str]
    delta: Optional[list]
    sektor_terdampak: Optional[list]
    dampak: Optional[str]
    watch: Optional[str]
    kontak: Optional[str]
    error: Optional[str]
    created_at: Optional[datetime]
    approved_at: Optional[datetime]
    analyzed_at: Optional[datetime]


class ConfigOut(BaseModel):
    key: str
    value: Optional[str]
    is_secret: bool


class ConfigIn(BaseModel):
    value: Optional[str] = None


class CrawlResult(BaseModel):
    ran: bool
    started_at: datetime
    total_baru: int = 0
    total_ditemukan: int = 0
    per_source: dict = {}
    error: Optional[str] = None


class LoginIn(BaseModel):
    username: str
    password: str
