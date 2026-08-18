import certifi
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient | None = None
    db = None


db_instance = Database()


async def get_database():
    return db_instance.db


async def connect_to_mongo():
    try:
        db_instance.client = AsyncIOMotorClient(
            settings.mongodb_uri, tlsCAFile=certifi.where()
        )
        db_instance.db = db_instance.client.get_database("telegram_storage")
        logger.info("Connected to MongoDB")

        # Create indexes if possible; if this fails, log and continue.
        from app.repositories.mongodb.file_repository import file_repository

        try:
            await file_repository.create_indexes()
        except Exception as e:
            logger.exception("Failed to create file indexes: %s", e)

        from app.repositories.mongodb.user_repository import user_repository

        try:
            await user_repository.create_indexes()
        except Exception as e:
            logger.exception("Failed to create user indexes: %s", e)
            
        from app.repositories.mongodb.conversation_repository import conversation_repository
        
        try:
            await conversation_repository.create_indexes()
        except Exception as e:
            logger.exception("Failed to create conversation indexes: %s", e)

    except ServerSelectionTimeoutError as e:
        logger.error(
            "Could not connect to MongoDB (ServerSelectionTimeoutError). Continuing without DB. Error: %s",
            e,
        )
        db_instance.client = None
        db_instance.db = None
    except Exception as e:
        logger.exception("Unexpected error while connecting to MongoDB: %s", e)
        db_instance.client = None
        db_instance.db = None


async def close_mongo_connection():
    if db_instance.client:
        try:
            db_instance.client.close()
            logger.info("Closed MongoDB connection")
        except Exception:
            logger.exception("Error while closing MongoDB connection")
