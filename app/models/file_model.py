from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FileMetadata(BaseModel):
    id: str = Field(alias="_id")
    share_id: str
    owner_id: int
    chat_id: int
    telegram_file_id: str
    telegram_unique_id: str
    original_filename: str
    mime_type: str
    extension: str
    file_type: Optional[str] = None
    size: int
    r2_key: str
    bucket: str
    uploaded_at: datetime
    downloads: int = 0
    last_download: Optional[datetime] = None
    favorite: bool = False
    folder: Optional[str] = None
    deleted: bool = False

class ShareInfoResponse(BaseModel):
    share_id: str
    original_filename: str
    mime_type: str
    size: int
    uploaded_at: datetime
    downloads: int
