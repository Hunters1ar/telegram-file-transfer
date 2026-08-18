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

    async def get_files_for_user(self, owner_id: int, show_others: bool, limit: int = 50) -> list[FileMetadata]:
        if show_others:
            # Own files always included (any visibility).
            # Other users' files ONLY if explicitly set to public.
            query = {
                "$or": [
                    {"owner_id": owner_id},
                    {"owner_id": {"$ne": owner_id}, "sharing.mode": "public"}
                ]
            }
        else:
            query = {"owner_id": owner_id}
        cursor = self.collection.find(query).sort("uploaded_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [FileMetadata(**doc) for doc in docs]

    async def search_files_by_name(self, owner_id: int, query: str, limit: int = 50) -> list[FileMetadata]:
        cursor = self.collection.find({
            "owner_id": owner_id,
            "original_filename": {"$regex": query, "$options": "i"}
        }).sort("uploaded_at", -1).limit(limit)
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

    async def update(self, file_metadata: FileMetadata):
        file_dict = file_metadata.model_dump(by_alias=True)
        await self.collection.replace_one({"share_id": file_metadata.share_id}, file_dict)

    async def delete(self, share_id: str):
        await self.collection.delete_one({"share_id": share_id})

    async def clear_all(self):
        await self.collection.delete_many({})

    async def get_user_stats(self, owner_id: int) -> dict:
        pipeline = [
            {"$match": {"owner_id": owner_id}},
            {"$facet": {
                "totals": [
                    {"$group": {
                        "_id": None,
                        "total_files": {"$sum": 1},
                        "total_size": {"$sum": "$size"},
                        "total_downloads": {"$sum": "$download_count"},
                        "total_shared": {
                            "$sum": {"$cond": [{"$eq": ["$sharing.mode", "public"]}, 1, 0]}
                        }
                    }}
                ],
                "categories": [
                    {"$group": {"_id": "$category", "count": {"$sum": 1}}}
                ]
            }}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        stats = {
            "total_files": 0,
            "total_size": 0,
            "total_downloads": 0,
            "total_shared": 0,
            "files_by_type": {}
        }
        
        if result and result[0]["totals"]:
            totals = result[0]["totals"][0]
            stats["total_files"] = totals.get("total_files", 0)
            stats["total_size"] = totals.get("total_size", 0)
            stats["total_downloads"] = totals.get("total_downloads", 0)
            stats["total_shared"] = totals.get("total_shared", 0)
            
            for cat in result[0].get("categories", []):
                if cat["_id"]:
                    stats["files_by_type"][cat["_id"]] = cat["count"]
                    
        return stats

file_repository = FileRepository()
