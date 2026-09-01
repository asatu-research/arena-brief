"""Model ORM."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JdihSource(Base):
    __tablename__ = "jdih_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # misal "kemendag"
    nama: Mapped[str] = mapped_column(String(100))  # nama singkat
    full_name: Mapped[str] = mapped_column(String(200))
    adapter: Mapped[str] = mapped_column(String(60))  # nama adapter di crawlers/
    listing_url: Mapped[str] = mapped_column(Text)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_crawl_status: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    regulations: Mapped[list["Regulation"]] = relationship(back_populates="source")


class Regulation(Base):
    __tablename__ = "regulation"
    __table_args__ = (UniqueConstraint("source_id", "nomor", "judul", name="uq_reg_src_nomor_judul"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("jdih_source.id"), index=True)
    jenis: Mapped[str] = mapped_column(String(80))  # Peraturan Menteri, dst
    nomor: Mapped[str] = mapped_column(String(60))  # "No. 12 Tahun 2026"
    judul: Mapped[str] = mapped_column(Text)
    tanggal: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    url_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_pdf: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # triase
    triage_label: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # substantif/internal/ragu
    triage_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # analisis
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending/approved/skipped/analyzed/failed
    ringkas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delta: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    sektor_terdampak: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    dampak: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # high/med/low
    watch: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kontak: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    source: Mapped[JdihSource] = relationship(back_populates="regulations")


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)  # API keys dsb.
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
