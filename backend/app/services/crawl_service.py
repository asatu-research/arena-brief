"""Crawl service: jalankan semua adapter aktif, simpan regulasi baru (status pending)."""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crawlers import get_adapter
from app.crawlers.base import RawRegulation
from app.crawlers.engine import BrowserEngine, make_http_client
from app.models import JdihSource, Regulation

settings = get_settings()


async def crawl_all(db: AsyncSession) -> dict:
    """Crawl semua sumber aktif. Return ringkasan per sumber."""
    result = {"total_ditemukan": 0, "total_baru": 0, "per_source": {}}
    since = date.today() - timedelta(days=settings.crawl_days_back)

    sources = (await db.execute(select(JdihSource).where(JdihSource.aktif == True))).scalars().all()  # noqa: E712
    if not sources:
        result["error"] = "Tidak ada sumber aktif."
        return result

    http = await make_http_client()
    browser = BrowserEngine()
    try:
        for src in sources:
            adapter_cls = get_adapter(src.adapter)
            if not adapter_cls:
                src.last_crawl_status = "Adapter tidak ditemukan"
                continue
            src.last_crawl_at = datetime.utcnow()
            try:
                adapter = adapter_cls(src.listing_url, http, browser)
                raws = await adapter.fetch(since)
                # enrich item tanpa tanggal (untuk sumber yang tanggalnya di detail)
                for raw in raws:
                    if raw.tanggal is None and hasattr(adapter, "enrich"):
                        try:
                            raw = await adapter.enrich(raw)
                        except Exception:
                            pass
                baru = await _save_raw(db, src, raws)
                result["per_source"][src.key] = {"ditemukan": len(raws), "baru": baru}
                result["total_ditemukan"] += len(raws)
                result["total_baru"] += baru
                src.last_crawl_status = f"OK: {len(raws)} ditemukan, {baru} baru"
            except Exception as e:  # noqa: BLE001
                src.last_crawl_status = f"GAGAL: {e}"
                result["per_source"][src.key] = {"ditemukan": 0, "baru": 0, "error": str(e)}
        await db.commit()
    finally:
        await browser.close()
        await http.aclose()
    # triase: label substantif/internal untuk item pending tanpa label
    result["triage"] = await run_triage(db)
    return result


async def run_triage(db: AsyncSession) -> dict:
    """Berikan label triase (substantif/internal/ragu) ke regulasi pending yang belum dilabeli."""
    try:
        from app.ai.triage import triage_regs
        from app.models import AppConfig

        rows = (await db.execute(select(AppConfig))).scalars().all()
        cfg = {r.key: r.value for r in rows}
        provider = (cfg.get("TRIAGE_PROVIDER") or "grok").strip()
        model = (cfg.get("TRIAGE_MODEL") or "").strip() or None

        regs = (
            await db.execute(
                select(Regulation)
                .where(Regulation.status == "pending", Regulation.triage_label.is_(None))
                .order_by(Regulation.tanggal.desc())
                .limit(100)
            )
        ).scalars().all()
        if not regs:
            return {"diproses": 0, "msg": "tidak ada yang perlu ditriase"}
        labels = await triage_regs(regs, provider=provider, model=model)
        for r in regs:
            if r.id in labels:
                r.triage_label = labels[r.id]["label"]
                r.triage_summary = labels[r.id]["ringkasan"]
        await db.commit()
        return {"diproses": len(labels), "provider": provider}
    except Exception as e:  # noqa: BLE001
        return {"diproses": 0, "error": str(e)}


async def _save_raw(db: AsyncSession, src: JdihSource, raws: list[RawRegulation]) -> int:
    """Simpan regulasi baru (dedupe by source+nomor+judul). Return jumlah baru."""
    baru = 0
    existing = set()
    if raws:
        rows = (
            await db.execute(
                select(Regulation.nomor, Regulation.judul).where(Regulation.source_id == src.id)
            )
        ).all()
        existing = {(r.nomor, r.judul) for r in rows}
    for raw in raws:
        if (raw.nomor, raw.judul) in existing:
            continue
        reg = Regulation(
            source_id=src.id,
            jenis=raw.jenis,
            nomor=raw.nomor,
            judul=raw.judul,
            tanggal=raw.tanggal,
            url_detail=raw.url_detail,
            url_pdf=raw.url_pdf,
            status="pending",
        )
        db.add(reg)
        existing.add((raw.nomor, raw.judul))
        baru += 1
    return baru
