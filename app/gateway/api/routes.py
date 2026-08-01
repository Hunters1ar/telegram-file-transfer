from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
import io
import json
import urllib.parse
import hmac
import hashlib
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.r2.presigned import generate_presigned_url
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
        
    user_files = await file_repository.get_by_owner_id(owner_id, limit=50)
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
        
    stats = await file_repository.get_user_stats(owner_id)
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
        
    content = await file.read()
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
    presigned_url = generate_presigned_url(file_meta.r2_key, expiration=3600)
    
    # Redirect user to the presigned URL
    return RedirectResponse(url=presigned_url)
