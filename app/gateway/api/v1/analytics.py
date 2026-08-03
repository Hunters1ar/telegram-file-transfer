from fastapi import APIRouter, Depends
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.mongodb.settings_repository import settings_repository
from app.gateway.api.v1.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_stats(user: dict = Depends(get_current_user)):
    stats = await file_repository.get_user_stats(int(user['id']))
    limit_mb = await settings_repository.get_global_file_limit()
    stats["limit_mb"] = limit_mb
    return stats
