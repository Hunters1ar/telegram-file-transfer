from typing import List
from datetime import datetime, timezone
import logging
from app.repositories.mongodb.mongo import get_database

logger = logging.getLogger(__name__)

class AdminMemoryRepository:
    collection_name = 'admin_memories'

    async def _get_collection(self):
        db = await get_database()
        if db is not None:
            return db[self.collection_name]
        return None

    async def add_memory(self, admin_id: int, fact: str) -> bool:
        collection = await self._get_collection()
        if collection is None:
            return False
            
        doc = {
            'admin_id': admin_id,
            'fact': fact,
            'created_at': datetime.now(timezone.utc)
        }
        await collection.insert_one(doc)
        return True

    async def get_memories(self, admin_id: int) -> List[str]:
        collection = await self._get_collection()
        if collection is None:
            return []
            
        cursor = collection.find({'admin_id': admin_id}).sort('created_at', 1)
        docs = await cursor.to_list(length=None)
        return [doc['fact'] for doc in docs]

    async def clear_memories(self, admin_id: int):
        collection = await self._get_collection()
        if collection is not None:
            await collection.delete_many({'admin_id': admin_id})

admin_memory_repository = AdminMemoryRepository()
