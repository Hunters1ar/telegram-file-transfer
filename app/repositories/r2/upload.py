from typing import BinaryIO
from app.repositories.r2.r2_service import s3_client
from app.core.config import settings
import asyncio
from fastapi.concurrency import run_in_threadpool

async def upload_file_to_r2(file_stream: BinaryIO, r2_key: str, content_type: str = "application/octet-stream") -> str:
    """Uploads a file stream to Cloudflare R2 and returns the key."""
    
    def _upload():
        s3_client.upload_fileobj(
            file_stream,
            settings.r2_bucket_name,
            r2_key,
            ExtraArgs={
                "ContentType": content_type
            }
        )
    
    await run_in_threadpool(_upload)
    return r2_key
