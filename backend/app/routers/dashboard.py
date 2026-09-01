"""Router dashboard: read-only, tanpa auth (untuk halaman index.html)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Regulation
from app.schemas import RegulationOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _reg_out(r: Regulation) -> RegulationOut:
    out = RegulationOut.model_validate(r)
    out.source_key = r.source.key if r.source else ""
    out.source_nama = r.source.nama if r.source else ""
    return out


@router.get("/regulations")
async def dashboard_regs(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Regulation).where(Regulation.status == "analyzed").order_by(Regulation.tanggal.desc())
        )
    ).scalars().all()
    return [_reg_out(r) for r in rows]


@router.get("/counts")
async def counts(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(Regulation))).scalars().all()
    analyzed = [r for r in total if r.status == "analyzed"]
    pending = [r for r in total if r.status == "pending"]
    return {"total": len(total), "analyzed": len(analyzed), "pending": len(pending)}
