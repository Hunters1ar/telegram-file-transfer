from typing import Optional
from pymongo import IndexModel, ASCENDING
from app.repositories.mongodb.mongo import db_instance
from app.domain.entities.user import User

class UserRepository:
    def __init__(self):
        self._cache = {}

    @property
    def collection(self):
        return db_instance.db["users"]

    async def create_indexes(self):
        indexes = [
            IndexModel([("telegram_id", ASCENDING)], unique=True),
        ]
        await self.collection.create_indexes(indexes)

    async def upsert_user(self, user: User) -> User:
        update_data = {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        if user.language:
            update_data["language"] = user.language

        await self.collection.update_one(
            {"telegram_id": user.telegram_id},
            {
                "$set": update_data,
                "$setOnInsert": {
                    "show_others_files": True,
                    "affection": 0,
                    "anger": 0,
                    "trust": 0,
                    "closeness": 0,
                    "embarrassment": 0,
                    "jealousy": 0,
                    "pride": 50,
                    "created_at": user.created_at,
                }
            },
            upsert=True
        )
        self._cache[user.telegram_id] = user
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        if telegram_id in self._cache:
            return self._cache[telegram_id]
            
        doc = await self.collection.find_one({"telegram_id": telegram_id})
        if doc:
            user = User(**doc)
            self._cache[telegram_id] = user
            return user
        return None

    async def get_all_users(self) -> list[User]:
        cursor = self.collection.find().sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [User(**doc) for doc in docs]

    async def toggle_show_others_files(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            new_value = not getattr(user, 'show_others_files', True)
            await self.collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"show_others_files": new_value}}
            )
            user.show_others_files = new_value
            self._cache[telegram_id] = user
            return new_value
        return True

    async def set_language(self, telegram_id: int, language: str):
        await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"language": language}}
        )
        if telegram_id in self._cache:
            self._cache[telegram_id].language = language

    async def update_user_stats(self, telegram_id: int, deltas: dict) -> User | None:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        
        update_fields = {}
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        stat_keys = ["affection", "anger", "trust", "closeness", "embarrassment", "jealousy", "pride"]
        for stat in stat_keys:
            if stat in deltas:
                delta = deltas[stat]
                current = getattr(user, stat, 0)
                if current is None:
                    current = 50 if stat == "pride" else 0
                    
                new_val = max(0, min(100, current + delta))
                if new_val != current:
                    update_fields[stat] = new_val
                    setattr(user, stat, new_val)
                    if stat in ["affection", "anger"]:
                        update_fields[f"last_{stat}_update"] = now
                        setattr(user, f"last_{stat}_update", now)
            
        if update_fields:
            await self.collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": update_fields}
            )
            # Update cache
            self._cache[telegram_id] = user
            
        return user

user_repository = UserRepository()
