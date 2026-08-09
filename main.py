import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
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
        await bot.set_webhook(f"https://api.hunterstar.online/webhook")
        from app.clients.telegram.bot import setup_bot_commands
        await setup_bot_commands(bot)
        
    yield
    
    # Shutdown
    if bot_task:
        bot_task.cancel()
    if settings.bot_mode == "polling":
        await bot.session.close()
        
    await close_mongo_connection()

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
WEBSITE_DIR = os.path.join(os.path.dirname(__file__), "website")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

@app.get("/app/{path:path}")
async def serve_webapp(path: str = ""):
    if not path or path == "index.html":
        return FileResponse(os.path.join(WEBSITE_DIR, "index.html"), media_type="text/html", headers=NO_CACHE_HEADERS)
    file_path = os.path.join(WEBSITE_DIR, path)
    if os.path.isfile(file_path):
        # Always serve JS, CSS, and service worker fresh — never cached
        ext = os.path.splitext(path)[1].lower()
        if ext in (".js", ".css"):
            return FileResponse(file_path, headers=NO_CACHE_HEADERS)
        return FileResponse(file_path)
    # SPA fallback
    return FileResponse(os.path.join(WEBSITE_DIR, "index.html"), media_type="text/html", headers=NO_CACHE_HEADERS)
