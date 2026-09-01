"""Router crawl: dipanggil n8n (cron Jumat) atau manual dari admin."""
from fastapi import APIRouter, Depends

from app.database import get_db
from app.services.crawl_service import crawl_all
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/crawl", tags=["crawl"])


@router.post("/run")
async def run_crawl(db: AsyncSession = Depends(get_db)):
    result = await crawl_all(db)
    return result
