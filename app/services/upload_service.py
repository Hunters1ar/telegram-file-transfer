import io
import uuid
from datetime import datetime, timezone
from app.domain.entities.file import FileMetadata, FileStatus
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.r2.upload import upload_file_to_r2
from app.services.share_service import share_service
from app.events.bus import event_bus, Events
from app.core.config import settings

from typing import Optional

class UploadService:
    async def process_upload(
        self, 
        file_stream: io.BytesIO, 
        owner_id: int, 
        chat_id: int, 
        original_filename: str, 
        mime_type: str, 
        size: int,
        category: str,
        telegram_file_id: Optional[str] = None,
        telegram_unique_id: Optional[str] = None
    ) -> FileMetadata:
        
        # 1. Deduplication Check (Instant Upload)
        if telegram_unique_id:
            existing_doc = await file_repository.get_by_telegram_unique_id(telegram_unique_id)
            if existing_doc and existing_doc.owner_id == owner_id:
                # We already have this file for this owner! Instant upload.
                print("Instant Upload triggered for file_unique_id:", telegram_unique_id)
                return existing_doc
            
        # 2. Upload to R2
        r2_key = share_service.generate_r2_key(owner_id, original_filename)
        await upload_file_to_r2(file_stream, r2_key, mime_type)
        
        # 3. Create Metadata
        share_id = await share_service.get_unique_share_id()
        
        ext = ""
        if "." in original_filename:
            ext = "." + original_filename.split(".")[-1]
            
        file_metadata = FileMetadata(
            _id=str(uuid.uuid4()),
            share_id=share_id,
            owner_id=owner_id,
            chat_id=chat_id,
            original_filename=original_filename,
            mime_type=mime_type,
            extension=ext,
            category=category,
            size=size,
            telegram_file_id=telegram_file_id,
            telegram_file_unique_id=telegram_unique_id,
            r2_bucket=settings.r2_bucket_name,
            r2_object_key=r2_key,
            status=FileStatus.ACTIVE,
            uploaded_at=datetime.now(timezone.utc)
        )
        
        # 4. Save to DB
        await file_repository.save(file_metadata)
        
        # 5. Emit Event
        await event_bus.publish(Events.FILE_CREATED, file_metadata)
        
        return file_metadata

    async def process_virtual_upload(
        self,
        owner_id: int,
        chat_id: int,
        original_filename: str,
        mime_type: str,
        size: int,
        category: str,
        telegram_file_id: str,
        telegram_unique_id: str
    ) -> FileMetadata:
        # Deduplication Check
        existing_doc = await file_repository.get_by_telegram_unique_id(telegram_unique_id)
        if existing_doc and existing_doc.owner_id == owner_id:
            return existing_doc
            
        share_id = await share_service.get_unique_share_id()
        
        ext = ""
        if "." in original_filename:
            ext = "." + original_filename.split(".")[-1]
            
        file_metadata = FileMetadata(
            _id=str(uuid.uuid4()),
            share_id=share_id,
            owner_id=owner_id,
            chat_id=chat_id,
            original_filename=original_filename,
            mime_type=mime_type,
            extension=ext,
            category=category,
            size=size,
            telegram_file_id=telegram_file_id,
            telegram_file_unique_id=telegram_unique_id,
            r2_bucket="virtual",
            r2_object_key="virtual",
            status=FileStatus.ACTIVE,
            uploaded_at=datetime.now(timezone.utc)
        )
        
        await file_repository.save(file_metadata)
        await event_bus.publish(Events.FILE_CREATED, file_metadata)
        
        return file_metadata


upload_service = UploadService()
