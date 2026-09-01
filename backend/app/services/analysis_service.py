"""Pipeline analisis: download PDF -> parse -> analisis AI."""
import datetime
import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analyze import analyze_reg
from app.ai.parse import parse_pdf
from app.crawlers import get_adapter
from app.models import AppConfig, Regulation


async def get_provider(db: AsyncSession) -> tuple[str, str]:
    """Provider & model dari AppConfig, default grok."""
    rows = (await db.execute(select(AppConfig))).scalars().all()
    cfg = {r.key: r.value for r in rows}
    provider = cfg.get("ANALYSIS_PROVIDER") or "grok"
    model = cfg.get("ANALYSIS_MODEL")
    return provider, model or ("" if provider != "grok" else None)


async def analyze_regulation(db: AsyncSession, reg: Regulation) -> Regulation:
    """Full pipeline untuk satu regulasi. Mengubah status di DB."""
    reg.status = "approved"
    reg.approved_at = datetime.datetime.utcnow()
    await db.flush()
    try:
        pdf = await _download_pdf(reg)
        if not pdf:
            raise RuntimeError("URL PDF tidak ditemukan.")
        text = await parse_pdf(pdf)
        provider, model = await get_provider(db)
        result = await analyze_reg(reg, text, provider=provider, model=model)
        reg.ringkas = result.get("ringkas", "")
        reg.delta = result.get("delta", [])
        reg.sektor_terdampak = result.get("sektor_terdampak", [])
        reg.dampak = result.get("dampak", "med")
        reg.watch = result.get("watch", "")
        reg.kontak = result.get("kontak", "")
        reg.status = "analyzed"
        reg.analyzed_at = datetime.datetime.utcnow()
        reg.error = None
    except Exception as e:  # noqa: BLE001
        reg.status = "failed"
        reg.error = str(e)
    await db.commit()
    return reg


async def _download_pdf(reg: Regulation) -> bytes | None:
    if not reg.url_pdf:
        # coba resolve via adapter detail
        adapter = get_adapter(reg.source.adapter if reg.source else None)
        if adapter:
            inst = adapter("", httpx.AsyncClient())
            if hasattr(inst, "enrich"):
                # butuh reg.source; skip bila tidak ada
                pass
        return None
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0, verify=False) as client:
        resp = await client.get(reg.url_pdf, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None
        if resp.headers.get("content-type", "").startswith("text/html"):
            return None
        return resp.content
