from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import io

from app.gateway.api.v1.auth import get_current_user
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.mongodb.settings_repository import settings_repository
from app.repositories.r2.presigned import generate_presigned_put_url
from app.services.share_service import share_service
from app.services.upload_service import upload_service
from app.events.bus import event_bus, Events
from app.domain.entities.file import FileMetadata, FileStatus
from app.core.config import settings

router = APIRouter()

class UploadRequestModel(BaseModel):
    name: str
    size: int
    mime_type: str
    sha256: Optional[str] = None # For smart upload deduplication

class UploadConfirmModel(BaseModel):
    name: str
    size: int
    mime_type: str
    r2_key: str

@router.post("/request")
async def request_upload(data: UploadRequestModel, user: dict = Depends(get_current_user)):
    # Check for deduplication (Smart Upload) if sha256 is provided
    # if data.sha256:
    #     existing_file = await file_repository.get_by_sha256(data.sha256)
    #     if existing_file:
    #         # handle instant upload by copying metadata
    #         pass
            
    r2_key = share_service.generate_r2_key(user['id'], data.name)
    url = generate_presigned_put_url(r2_key, data.mime_type)
    
    return {"url": url, "r2_key": r2_key}

@router.post("/confirm")
async def confirm_upload(data: UploadConfirmModel, user: dict = Depends(get_current_user)):
    if data.mime_type.startswith("image/"): category = "photo"
    elif data.mime_type.startswith("video/"): category = "video"
    elif data.mime_type.startswith("audio/"): category = "audio"
    else: category = "document"
    
    share_id = await share_service.get_unique_share_id()
    ext = ""
    if "." in data.name:
        ext = "." + data.name.split(".")[-1]
        
    file_metadata = FileMetadata(
        _id=str(uuid.uuid4()),
        share_id=share_id,
        owner_id=int(user['id']),
        chat_id=int(user['id']),
        original_filename=data.name,
        mime_type=data.mime_type,
        extension=ext,
        category=category,
        size=data.size,
        r2_bucket=settings.r2_bucket_name,
        r2_object_key=data.r2_key,
        status=FileStatus.ACTIVE,
        uploaded_at=datetime.now(timezone.utc)
    )
    await file_repository.save(file_metadata)
    await event_bus.publish(Events.FILE_CREATED, file_metadata)
    
    return {
        "id": file_metadata.share_id,
        "name": file_metadata.original_filename,
        "size": file_metadata.size
    }

# Kept for bot or simple clients
@router.post("/")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    limit_mb = await settings_repository.get_global_file_limit()
    
    if hasattr(file, "size") and file.size is not None and file.size > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {limit_mb}MB.")
        
    content = await file.read()
    if len(content) > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {limit_mb}MB.")
        
    file_stream = io.BytesIO(content)
    mime_type = file.content_type or "application/octet-stream"
    
    if mime_type.startswith("image/"): category = "photo"
    elif mime_type.startswith("video/"): category = "video"
    elif mime_type.startswith("audio/"): category = "audio"
    else: category = "document"

    file_meta = await upload_service.process_upload(
        file_stream=file_stream,
        owner_id=int(user['id']),
        chat_id=int(user['id']),
        original_filename=file.filename,
        mime_type=mime_type,
        size=len(content),
        category=category
    )
    
    return {
        "id": file_meta.share_id,
        "name": file_meta.original_filename,
        "size": file_meta.size
    }
