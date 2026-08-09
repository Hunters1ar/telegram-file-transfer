from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from app.repositories.mongodb.file_repository import file_repository
from app.gateway.api.v1.auth import get_current_user
from app.repositories.r2.r2_service import delete_file_from_r2

router = APIRouter()

@router.get("/")
async def get_files(user: dict = Depends(get_current_user)):
    from app.repositories.mongodb.user_repository import user_repository
    owner_id = int(user['id'])
    user_model = await user_repository.get_by_telegram_id(owner_id)
    show_others = getattr(user_model, 'show_others_files', True) if user_model else True
    
    user_files = await file_repository.get_files_for_user(owner_id, show_others, limit=50)
    return [
        {
            "id": f.share_id,
            "name": f.original_filename,
            "size": f.size,
            "category": f.category,
            "sharing": f.sharing.mode,
            "uploaded_at": f.uploaded_at
        } for f in user_files
    ]

class FileUpdateModel(BaseModel):
    name: Optional[str] = None
    sharing: Optional[str] = None  # 'public' or 'private'

@router.patch("/{share_id}")
async def update_file(share_id: str, update_data: FileUpdateModel, user: dict = Depends(get_current_user)):
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta or file_meta.owner_id != int(user['id']):
        raise HTTPException(status_code=404, detail="File not found")
        
    if update_data.name is not None:
        file_meta.original_filename = update_data.name
    if update_data.sharing == 'public':
        file_meta.sharing.mode = 'public'
    elif update_data.sharing == 'private':
        file_meta.sharing.mode = 'private'
        
    await file_repository.update(file_meta)
    return {"status": "ok"}

@router.delete("/{share_id}")
async def delete_file_endpoint(share_id: str, user: dict = Depends(get_current_user)):
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta or file_meta.owner_id != int(user['id']):
        raise HTTPException(status_code=404, detail="File not found")
        
    await delete_file_from_r2(file_meta.r2_object_key)
    await file_repository.delete(share_id)
    
    return {"status": "ok"}

# Unauthenticated public endpoint for preview page
@router.get("/public/{share_id}")
async def get_public_file(share_id: str):
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Anyone can see file metadata to render the preview page
    # Actual downloading is still protected by download endpoint
    return {
        "id": file_meta.share_id,
        "name": file_meta.original_filename,
        "size": file_meta.size,
        "category": file_meta.category,
        "uploaded_at": file_meta.uploaded_at,
        "owner_id": file_meta.owner_id
    }
