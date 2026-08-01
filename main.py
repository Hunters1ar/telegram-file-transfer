import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.repositories.mongodb.mongo import connect_to_mongo, close_mongo_connection
from app.gateway.api.routes import router as api_router
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
        logging.info("Webhook mode is configured, but not fully implemented in this example yet.")
        # Setup webhook URL here in the future
        
    yield
    
    # Shutdown
    if bot_task:
        bot_task.cancel()
    if settings.bot_mode == "polling":
        await bot.session.close()
        
    await close_mongo_connection()

app = FastAPI(title="Telegram Storage API", lifespan=lifespan)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Telegram Storage API is running."}
