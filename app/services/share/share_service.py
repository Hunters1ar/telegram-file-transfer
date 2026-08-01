import random
import string
import uuid
from datetime import datetime, timezone
from app.repositories.file_repository import file_repository

class ShareService:
    @staticmethod
    def generate_share_id(length: int = 6) -> str:
        """Generate a random alphanumeric uppercase share ID."""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    @staticmethod
    def generate_r2_key(owner_id: int, original_filename: str) -> str:
        """Generate a structured R2 key: users/{owner_id}/{year}/{month}/{uuid}{ext}"""
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        unique_id = str(uuid.uuid4())
        
        # Extract extension
        ext = ""
        if "." in original_filename:
            ext = "." + original_filename.split(".")[-1]
            
        return f"users/{owner_id}/{year}/{month}/{unique_id}{ext}"

    async def get_unique_share_id(self) -> str:
        """Ensure the generated share ID does not exist in the database."""
        while True:
            share_id = self.generate_share_id()
            existing_doc = await file_repository.get_by_share_id(share_id)
            if not existing_doc:
                return share_id

share_service = ShareService()
