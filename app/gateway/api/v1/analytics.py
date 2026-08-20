from fastapi import APIRouter, Depends
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.mongodb.settings_repository import settings_repository
from app.repositories.mongodb.user_repository import user_repository
from app.gateway.api.v1.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

@router.get("/")
async def get_stats(user: dict = Depends(get_current_user)):
    stats = await file_repository.get_user_stats(int(user['id']))
    limit_mb = await settings_repository.get_global_file_limit()
    stats["limit_mb"] = limit_mb
    
    user_doc = await user_repository.get_by_telegram_id(int(user['id']))
    if user_doc and user_doc.language:
        stats["language"] = user_doc.language
        
    return stats

class LanguageUpdate(BaseModel):
    language: str

@router.post("/language")
async def update_language(data: LanguageUpdate, user: dict = Depends(get_current_user)):
    await user_repository.set_language(int(user['id']), data.language)
    return {"status": "ok"}

