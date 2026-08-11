from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from app.repositories.mongodb.file_repository import file_repository
from app.gateway.api.v1.auth import get_current_user
from app.repositories.r2.r2_service import delete_file_from_r2

router = APIRouter()

@router.get("/")
async def get_files(user: dict = Depends(get_current_user)):
    owner_id = int(user['id'])

    # IMPORTANT: The website dashboard ALWAYS shows only the current user's own files.
    # The "show_others_files" preference applies only to the Telegram bot's inline mode (@bot query).
    # Mixing other users' files into the dashboard would expose private file metadata.
    user_files = await file_repository.get_by_owner_id(owner_id, limit=50)
    return [
        {
            "id": f.share_id,
            "name": f.original_filename,
            "size": f.size,
            "category": f.category,
            "sharing": f.sharing.mode,
            "is_favorite": f.is_favorite,
            "folder_id": f.folder_id,
            "uploaded_at": f.uploaded_at
        } for f in user_files
    ]


class FileUpdateModel(BaseModel):
    name: Optional[str] = None
    sharing: Optional[str] = None  # 'public' or 'private'
    is_favorite: Optional[bool] = None
    folder_id: Optional[str] = None

@router.patch("/{share_id}")
async def update_file(share_id: str, update_data: FileUpdateModel, user: dict = Depends(get_current_user)):
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta or file_meta.owner_id != int(user['id']):
        raise HTTPException(status_code=404, detail="File not found")
        
    if update_data.name is not None:
        new_name = update_data.name
        if file_meta.extension and not new_name.endswith(file_meta.extension):
            # Try to prevent extension stacking if they typed the wrong extension
            if "." in new_name and 1 <= len(new_name.split(".")[-1]) <= 4:
                new_name = new_name.rsplit(".", 1)[0]
            new_name += file_meta.extension
        file_meta.original_filename = new_name
    if update_data.sharing == 'public':
        file_meta.sharing.mode = 'public'
    elif update_data.sharing == 'private':
        file_meta.sharing.mode = 'private'
        
    if update_data.is_favorite is not None:
        file_meta.is_favorite = update_data.is_favorite
        
    if update_data.folder_id is not None:
        # A special value like "root" or "" could mean remove from folder
        if update_data.folder_id in ["root", ""]:
            file_meta.folder_id = None
        else:
            file_meta.folder_id = update_data.folder_id
        
    await file_repository.update(file_meta)
    return {"status": "ok", "name": file_meta.original_filename}

@router.delete("/{share_id}")
async def delete_file_endpoint(share_id: str, user: dict = Depends(get_current_user)):
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta or file_meta.owner_id != int(user['id']):
        raise HTTPException(status_code=404, detail="File not found")
        
    await delete_file_from_r2(file_meta.r2_object_key)
    await file_repository.delete(share_id)
    
    return {"status": "ok"}

# Unauthenticated public endpoint for the file preview page.
# Only returns metadata for files that are explicitly set to public.
@router.get("/public/{share_id}")
async def get_public_file(share_id: str):
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")

    # Privacy gate: never expose metadata of private files to unauthenticated callers
    if file_meta.sharing.mode != "public":
        raise HTTPException(status_code=403, detail="This file is private")

    return {
        "id": file_meta.share_id,
        "name": file_meta.original_filename,
        "size": file_meta.size,
        "category": file_meta.category,
        "uploaded_at": file_meta.uploaded_at,
        # owner_id intentionally omitted — no need to expose internal user IDs publicly
    }
