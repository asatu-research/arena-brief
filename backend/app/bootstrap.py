"""Bootstrap: init DB + seed sumber default & config + sinkron config ke settings."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import Base, engine
from app.models import AppConfig, JdihSource

settings = get_settings()

DEFAULT_SOURCES = [
    {
        "key": "bkpm", "nama": "Kemeninves/BKPM", "full_name": "Kementerian Investasi/BKPM",
        "adapter": "bkpm",
        "listing_url": "https://jdih.bkpm.go.id/id/search?page=1&limit=50&keyword=&sort=desc_nulls_last&document_type=Peraturan&regulation_type=all&regulation_sub_type=Peraturan%20Menteri%20Investasi/Kepala%20BKPM&regulation_year=2026&id_theme=",
    },
    {
        "key": "kemenkeu", "nama": "Kemenkeu", "full_name": "Kementerian Keuangan",
        "adapter": "kemenkeu",
        "listing_url": "https://jdih.kemenkeu.go.id/search?order=desc&bentuk=Peraturan+Menteri&tahun=2026&page=1",
    },
    {
        "key": "kemendag", "nama": "Kemendag", "full_name": "Kementerian Perdagangan",
        "adapter": "kemendag",
        "listing_url": "https://jdih.kemendag.go.id/peraturan?search=&jenisreg=bc9d1e17-9cf1-4c60-b670-87814dca4df4&tahunreg=2026&tematik=&status=&order=terbaru&baseben_bot_trap=",
    },
    {
        "key": "kementan", "nama": "Kementan", "full_name": "Kementerian Pertanian",
        "adapter": "kementan",
        "listing_url": "https://jdih.pertanian.go.id/peraturan",
    },
    {
        "key": "kkp", "nama": "KKP", "full_name": "Kementerian Kelautan dan Perikanan",
        "adapter": "kkp",
        "listing_url": "https://jdih.kkp.go.id/Homedev/PeraturanAll",
    },
    {
        "key": "kemenperin", "nama": "Kemenperin", "full_name": "Kementerian Perindustrian",
        "adapter": "kemenperin",
        "listing_url": "https://jdih.kemenperin.go.id/dokumen/index?DokumenSearch%5Bjudul%5D=&DokumenSearch%5Btipe_dokumen%5D=1&DokumenSearch%5Bjenis_peraturan%5D=PERATURAN+MENTERI&DokumenSearch%5Bnomor_peraturan%5D=&DokumenSearch%5Btahun_terbit%5D=2026&DokumenSearch%5Bstatus_terakhir%5D=",
    },
    {
        "key": "esdm", "nama": "Kem ESDM", "full_name": "Kementerian Energi dan Sumber Daya Mineral",
        "adapter": "esdm",
        "listing_url": "https://jdih.esdm.go.id/dokumen/peraturan?DokumenSearch%5Bjudul%5D=&DokumenSearch%5Btipe_dokumen%5D=1&DokumenSearch%5Bjenis_peraturan%5D=175&DokumenSearch%5BtopicIds%5D=&DokumenSearch%5Bnomor_peraturan%5D=&DokumenSearch%5Btahun_terbit%5D=2026&DokumenSearch%5Bstatus_terakhir%5D=&DokumenSearch%5Bpenerbit%5D=&DokumenSearch%5Bbidang_hukum%5D=&DokumenSearch%5Bdaerah%5D=",
    },
    {
        "key": "kemenkes", "nama": "Kemenkes", "full_name": "Kementerian Kesehatan",
        "adapter": "kemkes",
        "listing_url": "https://jdih.kemkes.go.id/documents?selectedType=1&selectedYear=2026",
    },
    {
        "key": "kemnaker", "nama": "Kemnaker", "full_name": "Kementerian Ketenagakerjaan",
        "adapter": "kemnaker",
        "listing_url": "https://jdih.kemnaker.go.id/peraturan?sort=hierarki&jenis%5B%5D=8&semuajudul=&semuanomor=&semuatahun=",
    },
]

DEFAULT_CONFIG = [
    ("GROK_API_KEY", "", True),
    ("MISTRAL_API_KEY", "", True),
    ("DEEPSEEK_API_KEY", "", True),
    ("TRIAGE_PROVIDER", "grok", False),
    ("TRIAGE_MODEL", "", False),
    ("ANALYSIS_PROVIDER", "grok", False),
    ("ANALYSIS_MODEL", "", False),
]


async def load_db_config_to_settings():
    """Tarik nilai AppConfig dari DB ke settings (override env).

    Dengan ini, API key yang diisi lewat UI /admin langsung aktif tanpa restart.
    """
    async with AsyncSession(engine) as db:
        rows = (await db.execute(select(AppConfig))).scalars().all()
        for r in rows:
            attr = r.key.lower()
            if hasattr(settings, attr) and r.value:
                setattr(settings, attr, r.value)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as db:
        # seed sources
        existing = (await db.execute(select(JdihSource.key))).scalars().all()
        have = set(existing)
        for s in DEFAULT_SOURCES:
            if s["key"] not in have:
                db.add(JdihSource(**s))
        # seed config
        for key, value, is_secret in DEFAULT_CONFIG:
            row = await db.get(AppConfig, key)
            if row is None:
                db.add(AppConfig(key=key, value=value, is_secret=is_secret))
        await db.commit()
    await load_db_config_to_settings()
