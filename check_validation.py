import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.domain.entities.file import FileMetadata

async def check():
    client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    db = client.db
    files = db["files"]
    docs = await files.find().to_list(length=100)
    for doc in docs:
        try:
            FileMetadata(**doc)
        except Exception as e:
            print(f"Validation failed for doc {doc.get('_id')}: {e}")

asyncio.run(check())
