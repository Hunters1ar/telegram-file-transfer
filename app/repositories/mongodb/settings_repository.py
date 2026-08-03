from app.repositories.mongodb.mongo import db_instance

class SettingsRepository:
    @property
    def collection(self):
        return db_instance.db["settings"]
        
    async def get_global_file_limit(self) -> int:
        doc = await self.collection.find_one({"_id": "global"})
        if doc and "file_limit_mb" in doc:
            return doc["file_limit_mb"]
        return 20 # Default limit

    async def set_global_file_limit(self, limit_mb: int):
        await self.collection.update_one(
            {"_id": "global"},
            {"$set": {"file_limit_mb": limit_mb}},
            upsert=True
        )

settings_repository = SettingsRepository()
