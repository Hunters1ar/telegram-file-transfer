import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from app.core.config import settings
from app.repositories.mongodb.mongo import connect_to_mongo, close_mongo_connection
from app.gateway.api.v1.router import router as api_v1_router
from app.clients.telegram.bot import start_polling, bot

logging.basicConfig(level=logging.INFO)

# Background task reference
bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    
    global bot_task
    if settings.bot_mode == "polling":
        logging.info("Starting bot in polling mode...")
        bot_task = asyncio.create_task(start_polling())
    elif settings.bot_mode == "webhook":
        logging.info("Starting bot in webhook mode...")
        await bot.set_webhook(f"{settings.api_base_url.rstrip('/')}/webhook")
        from app.clients.telegram.bot import setup_bot_ui
        await setup_bot_ui(bot)
        
    yield
    
    # Shutdown
    if bot_task:
        bot_task.cancel()
    if settings.bot_mode == "polling":
        await bot.session.close()
        
    await close_mongo_connection()

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from aiogram import types as tg_types
import os

app = FastAPI(title="Telegram Storage API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")

# Alias: /api/v1/stats -> /api/v1/analytics
from app.gateway.api.v1.analytics import router as analytics_alias_router
app.include_router(analytics_alias_router, prefix="/api/v1/stats", tags=["Stats Alias"])

@app.get("/")
def read_root():
    return {"message": "Telegram Storage API is running."}

@app.post("/webhook")
async def telegram_webhook(update: dict):
    telegram_update = tg_types.Update(**update)
    from app.clients.telegram.bot import dp, bot
    await dp.feed_update(bot=bot, update=telegram_update)
    return {"status": "ok"}

# Serve the website frontend at /app/
WEBSITE_DIR = os.path.join(os.path.dirname(__file__), "website", "out")
WEBSITE_ROOT = os.path.abspath(WEBSITE_DIR)

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

STATIC_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=31536000, immutable"
}

PUBLIC_ASSETS = {
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "apple-touch-icon.png",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon.ico",
    "site.webmanifest",
    "sw.js",
}

def get_frontend_path(path: str) -> str:
    file_path = os.path.abspath(os.path.join(WEBSITE_ROOT, path))
    try:
        if os.path.commonpath([WEBSITE_ROOT, file_path]) != WEBSITE_ROOT:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=404, detail="Asset not found")
    return file_path

def get_frontend_index() -> str:
    index_path = get_frontend_path("index.html")
    if not os.path.isfile(index_path):
        raise HTTPException(
            status_code=503,
            detail="Frontend is not built. Run `cd website && npm ci && npm run build` before starting the server.",
        )
    return index_path

def frontend_file_response(path: str, headers: dict[str, str] | None = None, media_type: str | None = None):
    file_path = get_frontend_path(path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file_path, media_type=media_type, headers=headers)

@app.get("/_next/{path:path}")
async def serve_next_asset(path: str):
    return frontend_file_response(os.path.join("_next", path), headers=STATIC_CACHE_HEADERS)

@app.get("/icons/{path:path}")
async def serve_icon_asset(path: str):
    return frontend_file_response(os.path.join("icons", path), headers=STATIC_CACHE_HEADERS)

@app.get("/site.webmanifest")
@app.get("/sw.js")
@app.get("/favicon.ico")
@app.get("/favicon-16x16.png")
@app.get("/favicon-32x32.png")
@app.get("/apple-touch-icon.png")
@app.get("/android-chrome-192x192.png")
@app.get("/android-chrome-512x512.png")
async def serve_public_asset(request: Request):
    asset_name = request.url.path.lstrip("/")
    if asset_name not in PUBLIC_ASSETS:
        raise HTTPException(status_code=404, detail="Asset not found")
    headers = NO_CACHE_HEADERS if asset_name == "sw.js" else None
    return frontend_file_response(asset_name, headers=headers)

@app.get("/app")
async def serve_webapp_root():
    return FileResponse(get_frontend_index(), media_type="text/html", headers=NO_CACHE_HEADERS)

@app.get("/app/{path:path}")
async def serve_webapp(path: str = ""):
    if not path or path == "index.html":
        return FileResponse(get_frontend_index(), media_type="text/html", headers=NO_CACHE_HEADERS)
    file_path = get_frontend_path(path)
    if os.path.isfile(file_path):
        # Always serve JS, CSS, and service worker fresh — never cached
        ext = os.path.splitext(path)[1].lower()
        if ext in (".js", ".css"):
            return FileResponse(file_path, headers=NO_CACHE_HEADERS)
        return FileResponse(file_path)
    # SPA fallback
    return FileResponse(get_frontend_index(), media_type="text/html", headers=NO_CACHE_HEADERS)
