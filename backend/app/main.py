"""FastAPI entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import init_db
from app.routers import admin, auth, crawl, dashboard

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Arena Brief", version="0.1.0", lifespan=lifespan)


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(crawl.router)
app.include_router(dashboard.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/admin", include_in_schema=False)
async def admin_page():
    return FileResponse(STATIC_DIR / "admin" / "index.html")


@app.get("/", include_in_schema=False)
async def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard" / "index.html")
