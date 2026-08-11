from pydantic import BaseModel, Field
from datetime import datetime

class FolderMetadata(BaseModel):
    id: str = Field(alias="_id")
    name: str
    owner_id: int
    created_at: datetime
