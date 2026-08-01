from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.r2.presigned import generate_presigned_url

router = APIRouter()

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
