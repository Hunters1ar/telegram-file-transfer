from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
from app.repositories.mongodb.mongo import get_database

logger = logging.getLogger(__name__)

class ConversationRepository:
    collection_name = "ai_conversations"

    async def _get_collection(self):
        db = await get_database()
        if db is not None:
            return db[self.collection_name]
        return None

    async def create_indexes(self):
        collection = await self._get_collection()
        if collection is not None:
            import pymongo
            # Index by user_id for fast retrieval, and created_at for sorting/pruning
            await collection.create_index(
                [("user_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)]
            )
            logger.info("Created indexes for ai_conversations collection")

    async def add_message(self, user_id: int, message: Dict[str, Any]):
        """
        Adds a message to the conversation history.
        message should be a dict with keys: role, content, and optionally tool_calls, tool_call_id, name.
        """
        collection = await self._get_collection()
        if collection is None:
            return
            
        # Add metadata
        msg_doc = message.copy()
        msg_doc["user_id"] = user_id
        msg_doc["created_at"] = datetime.now(timezone.utc)
        
        await collection.insert_one(msg_doc)

    async def get_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves the last `limit` messages for the user.
        Returns them in chronological order.
        """
        collection = await self._get_collection()
        if collection is None:
            return []
            
        cursor = collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        # Reverse to get chronological order (oldest first)
        docs.reverse()
        
        messages = []
        for doc in docs:
            msg = {
                "role": doc["role"],
                "content": doc.get("content")
            }
            if "tool_calls" in doc and doc["tool_calls"]:
                msg["tool_calls"] = doc["tool_calls"]
            if "tool_call_id" in doc:
                msg["tool_call_id"] = doc["tool_call_id"]
            if "name" in doc:
                msg["name"] = doc["name"]
            messages.append(msg)
            
        return messages
        
    async def clear_history(self, user_id: int):
        collection = await self._get_collection()
        if collection is not None:
            await collection.delete_many({"user_id": user_id})

conversation_repository = ConversationRepository()
