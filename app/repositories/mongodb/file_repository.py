from typing import Optional
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.repositories.mongodb.mongo import db_instance
from app.domain.entities.file import FileMetadata

class FileRepository:
    @property
    def collection(self):
        return db_instance.db["files"]

    async def create_indexes(self):
        indexes = [
            IndexModel([("share_id", ASCENDING)], unique=True),
            IndexModel([("owner_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("sha256", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("folder_id", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("is_favorite", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("is_pinned", ASCENDING)]),
        ]
        await self.collection.create_indexes(indexes)
        print("MongoDB Indexes created.")

    async def save(self, file_metadata: FileMetadata) -> FileMetadata:
        file_dict = file_metadata.model_dump(by_alias=True)
        await self.collection.insert_one(file_dict)
        return file_metadata

    async def get_by_share_id(self, share_id: str) -> Optional[FileMetadata]:
        doc = await self.collection.find_one({"share_id": share_id})
        if doc:
            return FileMetadata(**doc)
        return None

    async def get_by_telegram_unique_id(self, telegram_unique_id: str) -> Optional[FileMetadata]:
        doc = await self.collection.find_one({"telegram_file_unique_id": telegram_unique_id})
        if doc:
            return FileMetadata(**doc)
        return None

    async def get_by_owner_id(self, owner_id: int, limit: int = 50) -> list[FileMetadata]:
        cursor = self.collection.find({"owner_id": owner_id}).sort("uploaded_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [FileMetadata(**doc) for doc in docs]

    async def increment_downloads(self, share_id: str, current_time):
        await self.collection.update_one(
            {"share_id": share_id},
            {
                "$inc": {"download_count": 1}, 
                "$set": {"last_download_at": current_time}
            }
        )

file_repository = FileRepository()
