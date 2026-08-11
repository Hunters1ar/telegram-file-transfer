from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone
from app.repositories.mongodb.folder_repository import folder_repository
from app.domain.entities.folder import FolderMetadata
from app.gateway.api.v1.auth import get_current_user

router = APIRouter()

class FolderCreateModel(BaseModel):
    name: str

@router.get("/")
async def get_folders(user: dict = Depends(get_current_user)):
    owner_id = int(user['id'])
    folders = await folder_repository.get_by_owner_id(owner_id)
    return [
        {
            "id": f.id,
            "name": f.name,
            "created_at": f.created_at
        } for f in folders
    ]

@router.post("/")
async def create_folder(data: FolderCreateModel, user: dict = Depends(get_current_user)):
    owner_id = int(user['id'])
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name cannot be empty")
        
    folder_id = str(uuid.uuid4())
    folder_meta = FolderMetadata(
        _id=folder_id,
        name=name,
        owner_id=owner_id,
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        await folder_repository.save(folder_meta)
    except Exception as e:
        # Assuming duplicate name error from MongoDB index
        if "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Folder with this name already exists")
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"status": "ok", "id": folder_id, "name": name}

@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, user: dict = Depends(get_current_user)):
    owner_id = int(user['id'])
    folder = await folder_repository.get_by_id(folder_id)
    
    if not folder or folder.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    await folder_repository.delete(folder_id)
    # Note: Files in this folder will effectively become "unfoldered".
    # In a full implementation, we might want to unset folder_id on files.
    
    return {"status": "ok"}
