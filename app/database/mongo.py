from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def get_database():
    return db_instance.db

async def connect_to_mongo():
    db_instance.client = AsyncIOMotorClient(settings.mongodb_uri)
    db_instance.db = db_instance.client.get_database("telegram_storage")
    print("Connected to MongoDB")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        print("Closed MongoDB connection")
