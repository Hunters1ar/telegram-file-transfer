from typing import List
from datetime import datetime, timezone
import logging
from app.repositories.mongodb.mongo import get_database

logger = logging.getLogger(__name__)

class UserMemoryRepository:
    """Stores persistent facts/memories about any user, not just the admin."""
    collection_name = 'user_memories'

    async def _get_collection(self):
        db = await get_database()
        if db is not None:
            return db[self.collection_name]
        return None

    async def add_memory(self, user_id: int, fact: str) -> bool:
        collection = await self._get_collection()
        if collection is None:
            return False
        doc = {
            'user_id': user_id,
            'fact': fact,
            'created_at': datetime.now(timezone.utc)
        }
        await collection.insert_one(doc)
        return True

    async def get_memories(self, user_id: int) -> List[str]:
        collection = await self._get_collection()
        if collection is None:
            return []
        cursor = collection.find({'user_id': user_id}).sort('created_at', 1)
        docs = await cursor.to_list(length=None)
        return [doc['fact'] for doc in docs]

    async def clear_memories(self, user_id: int):
        collection = await self._get_collection()
        if collection is not None:
            await collection.delete_many({'user_id': user_id})

user_memory_repository = UserMemoryRepository()
