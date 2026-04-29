from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from app.database import init_db, SessionLocal
from app.api.routes import router
from app.core.http_pool import init_http_client, close_http_client
from app.core.log_writer import start_log_consumer, shutdown_log_writer
from app.core.health import start_health_checker, restore_health_from_db, final_sync_health, _health_sync_loop
from app.core.cache import invalidate_all
from app.config import check_settings_reload
from sqlalchemy import select
from app.models import Channel
import asyncio

_health_checker_task = None
_health_sync_task = None
_config_reload_task = None

async def _config_reload_loop():
    """定期检查 .env 文件变更并热重载配置。"""
    while True:
        try:
            await asyncio.sleep(10)
            if check_settings_reload():
                invalidate_all()
        except asyncio.CancelledError:
            break
        except Exception:
            pass

class SPAMiddleware(BaseHTTPMiddleware):
    """SPA middleware: serve index.html for non-API 404s"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code == 404:
            path = request.url.path
            if not path.startswith("/api/") and not path.startswith("/v1/"):
                return FileResponse("app/static/dist/index.html")
        return response

async def _get_channel_ids():
    """获取所有渠道 ID 列表。"""
    async with SessionLocal() as db:
        result = await db.execute(select(Channel.id))
        return [row[0] for row in result.all()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_checker_task, _health_sync_task, _config_reload_task
    await init_db()
    init_http_client()
    start_log_consumer()
    await restore_health_from_db()
    _health_checker_task = asyncio.create_task(
        start_health_checker(lambda: SessionLocal(), _get_channel_ids)
    )
    _health_sync_task = asyncio.create_task(_health_sync_loop())
    _config_reload_task = asyncio.create_task(_config_reload_loop())
    yield
    if _health_checker_task and not _health_checker_task.done():
        _health_checker_task.cancel()
        try:
            await _health_checker_task
        except asyncio.CancelledError:
            pass
    if _health_sync_task and not _health_sync_task.done():
        _health_sync_task.cancel()
        try:
            await _health_sync_task
        except asyncio.CancelledError:
            pass
    if _config_reload_task and not _config_reload_task.done():
        _config_reload_task.cancel()
        try:
            await _config_reload_task
        except asyncio.CancelledError:
            pass
    await final_sync_health()
    await shutdown_log_writer()
    await close_http_client()

app = FastAPI(title="co-api", version="1.0.0", lifespan=lifespan)

# API routes FIRST (before middleware)
app.include_router(router)

# Static files (CSS, JS, images) - Vue3 build output
app.mount("/static", StaticFiles(directory="app/static/dist"), name="static_assets")

# Root route
@app.get("/")
async def serve_index():
    return FileResponse("app/static/dist/index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SPA middleware to handle client-side routing
app.add_middleware(SPAMiddleware)
