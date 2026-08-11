from typing import Optional
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.repositories.mongodb.mongo import db_instance
from app.domain.entities.folder import FolderMetadata

class FolderRepository:
    @property
    def collection(self):
        return db_instance.db["folders"]

    async def create_indexes(self):
        indexes = [
            IndexModel([("owner_id", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING), ("name", ASCENDING)], unique=True),
        ]
        await self.collection.create_indexes(indexes)
        print("MongoDB Folder Indexes created.")

    async def save(self, folder_metadata: FolderMetadata) -> FolderMetadata:
        folder_dict = folder_metadata.model_dump(by_alias=True)
        await self.collection.insert_one(folder_dict)
        return folder_metadata

    async def get_by_id(self, folder_id: str) -> Optional[FolderMetadata]:
        doc = await self.collection.find_one({"_id": folder_id})
        if doc:
            return FolderMetadata(**doc)
        return None

    async def get_by_owner_id(self, owner_id: int, limit: int = 100) -> list[FolderMetadata]:
        cursor = self.collection.find({"owner_id": owner_id}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [FolderMetadata(**doc) for doc in docs]

    async def delete(self, folder_id: str):
        await self.collection.delete_one({"_id": folder_id})

folder_repository = FolderRepository()
