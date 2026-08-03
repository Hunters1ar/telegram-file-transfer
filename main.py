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
from aiogram import types as tg_types

app = FastAPI(title="Telegram Storage API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Telegram Storage API is running."}

@app.post("/webhook")
async def telegram_webhook(update: dict):
    telegram_update = tg_types.Update(**update)
    from app.clients.telegram.bot import dp, bot
    await dp.feed_update(bot=bot, update=telegram_update)
    return {"status": "ok"}
