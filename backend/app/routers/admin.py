"""Router admin: kelola sumber, approval, konfigurasi, status."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AppConfig, JdihSource, Regulation
from app.schemas import ConfigIn, ConfigOut, RegulationOut, SourceIn, SourceOut
from app.security import require_admin
from app.services.analysis_service import analyze_regulation

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _reg_out(r: Regulation) -> RegulationOut:
    out = RegulationOut.model_validate(r)
    out.source_key = r.source.key if r.source else ""
    out.source_nama = r.source.nama if r.source else ""
    return out


@router.get("/regulations/pending")
async def pending_regs(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Regulation).where(Regulation.status.in_(["pending", "failed"])).order_by(Regulation.tanggal.desc())
        )
    ).scalars().all()
    return [_reg_out(r) for r in rows]


@router.get("/regulations/analyzed")
async def analyzed_regs(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Regulation).where(Regulation.status == "analyzed").order_by(Regulation.analyzed_at.desc())
        )
    ).scalars().all()
    return [_reg_out(r) for r in rows]


@router.post("/regulations/{reg_id}/approve")
async def approve_reg(reg_id: int, db: AsyncSession = Depends(get_db)):
    reg = await db.get(Regulation, reg_id)
    if not reg:
        raise HTTPException(404, "Regulasi tidak ditemukan")
    # analisis dijalankan sinkron supaya hasil langsung siap
    reg = await analyze_regulation(db, reg)
    return _reg_out(reg)


@router.post("/regulations/{reg_id}/skip")
async def skip_reg(reg_id: int, db: AsyncSession = Depends(get_db)):
    reg = await db.get(Regulation, reg_id)
    if not reg:
        raise HTTPException(404, "Regulasi tidak ditemukan")
    reg.status = "skipped"
    await db.commit()
    return {"ok": True}


# ── sumber ──────────────────────────────────────────────
@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(JdihSource).order_by(JdihSource.key))).scalars().all()
    return [SourceOut.model_validate(r) for r in rows]


@router.post("/sources")
async def create_source(body: SourceIn, db: AsyncSession = Depends(get_db)):
    src = JdihSource(**body.model_dump())
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return SourceOut.model_validate(src)


@router.put("/sources/{source_id}")
async def update_source(source_id: int, body: SourceIn, db: AsyncSession = Depends(get_db)):
    src = await db.get(JdihSource, source_id)
    if not src:
        raise HTTPException(404, "Sumber tidak ditemukan")
    for k, v in body.model_dump().items():
        setattr(src, k, v)
    await db.commit()
    await db.refresh(src)
    return SourceOut.model_validate(src)


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    src = await db.get(JdihSource, source_id)
    if not src:
        raise HTTPException(404, "Sumber tidak ditemukan")
    await db.delete(src)
    await db.commit()
    return {"ok": True}


# ── konfigurasi ─────────────────────────────────────────
@router.get("/config")
async def list_config(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AppConfig))).scalars().all()
    out = []
    for r in rows:
        c = ConfigOut(key=r.key, value=r.value, is_secret=r.is_secret)
        if r.is_secret and r.value:
            c.value = "[tersimpan]"  # mask
        out.append(c)
    return out


@router.put("/config/{key}")
async def update_config(key: str, body: ConfigIn, db: AsyncSession = Depends(get_db)):
    row = await db.get(AppConfig, key)
    if not row:
        row = AppConfig(key=key, value=body.value)
        db.add(row)
    else:
        row.value = body.value
    row.updated_at = datetime.utcnow()
    await db.commit()
    # terapkan langsung ke settings runtime (API key dll.)
    from app.bootstrap import load_db_config_to_settings
    await load_db_config_to_settings()
    return {"ok": True}


@router.get("/config/secret/{key}")
async def get_secret_config(key: str, db: AsyncSession = Depends(get_db)):
    """Ambil nilai secret (untuk melihat/uji koneksi API)."""
    row = await db.get(AppConfig, key)
    if not row:
        return {"key": key, "value": None}
    return {"key": key, "value": row.value}
