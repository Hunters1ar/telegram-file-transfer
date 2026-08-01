from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FileStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    ACTIVE = "active"
    TRASH = "trash"
    EXPIRED = "expired"
    FAILED = "failed"

class Permissions(BaseModel):
    download: bool = True
    share: bool = False
    rename: bool = True
    delete: bool = False

class SharingConfig(BaseModel):
    mode: str = "private" # "public", "private", "protected", etc.
    password_hash: Optional[str] = None
    expires_at: Optional[datetime] = None
    allowed_users: List[int] = [] 
    permissions: Permissions = Permissions()

class FileMetadata(BaseModel):
    id: str = Field(alias="_id")
    share_id: str
    
    # Ownership
    owner_id: int
    owner_username: Optional[str] = None
    owner_first_name: Optional[str] = None
    chat_id: int # Kept for Telegram notification references
    
    # Type Metadata
    original_filename: str
    mime_type: str
    extension: str
    category: str # 'video', 'image', 'document', 'audio'
    size: int
    sha256: Optional[str] = None 
    telegram_file_id: Optional[str] = None 
    telegram_file_unique_id: Optional[str] = None
    
    # R2 Storage Metadata
    r2_bucket: str
    r2_object_key: str
    r2_etag: Optional[str] = None
    storage_class: str = "STANDARD"
    
    # State & Organization
    status: FileStatus = FileStatus.ACTIVE
    sharing: SharingConfig = SharingConfig()
    is_favorite: bool = False
    is_pinned: bool = False
    tags: List[str] = []
    folder_id: Optional[str] = None
    
    # Analytics
    uploaded_at: datetime
    download_count: int = 0
    unique_download_count: int = 0
    first_download_at: Optional[datetime] = None
    last_download_at: Optional[datetime] = None
    last_download_by: Optional[int] = None
    unique_downloaders: List[int] = []
    
    # Trash System
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[int] = None
