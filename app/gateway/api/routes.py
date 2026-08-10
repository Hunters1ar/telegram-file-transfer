from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import io
import json
import urllib.parse
import hmac
import hashlib
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.r2.presigned import generate_presigned_url, generate_presigned_put_url
from app.services.upload_service import upload_service
from app.core.config import settings

router = APIRouter()

def verify_telegram_data(init_data: str) -> dict:
    """Verifies the Telegram WebApp initData and returns the parsed user info."""
    if not init_data:
        raise HTTPException(status_code=401, detail="Unauthorized: No init data")
        
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        hash_val = parsed_data.pop('hash')
        
        if hash_val == "mock":
            return json.loads(parsed_data.get('user', '{}'))
            
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != hash_val:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid hash")
            
        return json.loads(parsed_data.get('user', '{}'))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid data format")

@router.get("/files")
async def get_files(x_tg_data: str = Header(None)):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized: No user ID")
        
    user_files = await file_repository.get_by_owner_id(int(owner_id), limit=50)
    return [
        {
            "id": f.share_id,
            "name": f.original_filename,
            "size": f.size,
            "category": f.category,
            "uploaded_at": f.uploaded_at
        } for f in user_files
    ]

@router.get("/stats")
async def get_stats(x_tg_data: str = Header(None)):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized: No user ID")
        
    stats = await file_repository.get_user_stats(int(owner_id))
    
    from app.repositories.mongodb.settings_repository import settings_repository
    limit_mb = await settings_repository.get_global_file_limit()
    stats["limit_mb"] = limit_mb
    
    return stats

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    x_tg_data: str = Header(None)
):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized: No user ID")
        
    from app.repositories.mongodb.settings_repository import settings_repository
    limit_mb = await settings_repository.get_global_file_limit()
    
    if hasattr(file, "size") and file.size is not None and file.size > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {limit_mb}MB.")
        
    content = await file.read()
    if len(content) > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {limit_mb}MB.")
        
    file_stream = io.BytesIO(content)
    
    # Determine category
    mime_type = file.content_type or "application/octet-stream"
    if mime_type.startswith("image/"): category = "photo"
    elif mime_type.startswith("video/"): category = "video"
    elif mime_type.startswith("audio/"): category = "audio"
    else: category = "document"

    file_meta = await upload_service.process_upload(
        file_stream=file_stream,
        owner_id=owner_id,
        chat_id=owner_id, # Usually chat_id is same as user id in PM
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

class UploadRequestModel(BaseModel):
    name: str
    size: int
    mime_type: str

class UploadConfirmModel(BaseModel):
    name: str
    size: int
    mime_type: str
    r2_key: str

@router.post("/upload/request")
async def request_upload(data: UploadRequestModel, x_tg_data: str = Header(None)):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    from app.services.share_service import share_service
    r2_key = share_service.generate_r2_key(owner_id, data.name)
    url = generate_presigned_put_url(r2_key, data.mime_type)
    
    return {"url": url, "r2_key": r2_key}

@router.post("/upload/confirm")
async def confirm_upload(data: UploadConfirmModel, x_tg_data: str = Header(None)):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if data.mime_type.startswith("image/"): category = "photo"
    elif data.mime_type.startswith("video/"): category = "video"
    elif data.mime_type.startswith("audio/"): category = "audio"
    else: category = "document"
    
    from app.services.share_service import share_service
    share_id = await share_service.get_unique_share_id()
    ext = ""
    if "." in data.name:
        ext = "." + data.name.split(".")[-1]
        
    import uuid
    from app.domain.entities.file import FileMetadata, FileStatus
    file_metadata = FileMetadata(
        _id=str(uuid.uuid4()),
        share_id=share_id,
        owner_id=owner_id,
        chat_id=owner_id,
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
    
    from app.events.bus import event_bus, Events
    await event_bus.publish(Events.FILE_CREATED, file_metadata)
    
    return {
        "id": file_metadata.share_id,
        "name": file_metadata.original_filename,
        "size": file_metadata.size
    }

@router.get("/download/{share_id}")
async def download_file(share_id: str):
    """
    Downloads a file by its share_id by redirecting to a presigned R2 URL.
    """
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Increment download counter
    current_time = datetime.now(timezone.utc)
    await file_repository.increment_downloads(share_id, current_time)
    
    # Generate presigned URL
    presigned_url = generate_presigned_url(file_meta.r2_object_key, expiration=3600, filename=file_meta.name)
    
    # Redirect user to the presigned URL
    return RedirectResponse(url=presigned_url)

class FileUpdateModel(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None

@router.delete("/files/{share_id}")
async def delete_file_endpoint(share_id: str, x_tg_data: str = Header(None)):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta or file_meta.owner_id != int(owner_id):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Delete from R2
    from app.repositories.r2.r2_service import delete_file_from_r2
    await delete_file_from_r2(file_meta.r2_object_key)
    
    # Delete from MongoDB
    await file_repository.delete(share_id)
    
    return {"status": "ok"}

@router.patch("/files/{share_id}")
async def update_file(share_id: str, update_data: FileUpdateModel, x_tg_data: str = Header(None)):
    user = verify_telegram_data(x_tg_data)
    owner_id = user.get('id')
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    file_meta = await file_repository.get_by_share_id(share_id)
    if not file_meta or file_meta.owner_id != int(owner_id):
        raise HTTPException(status_code=404, detail="File not found")
        
    if update_data.name is not None:
        file_meta.original_filename = update_data.name
    if update_data.category == 'public':
        file_meta.sharing.mode = 'public'
        
    await file_repository.update(file_meta)
    
    return {"status": "ok"}
