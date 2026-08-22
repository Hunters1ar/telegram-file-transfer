from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

def get_utc_now():
    return datetime.now(timezone.utc)

class User(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None
    show_others_files: bool = True
    affection: int = Field(default=0, ge=0, le=100)
    anger: int = Field(default=0, ge=0, le=100)
    trust: int = Field(default=0, ge=0, le=100)
    closeness: int = Field(default=0, ge=0, le=100)
    embarrassment: int = Field(default=0, ge=0, le=100)
    jealousy: int = Field(default=0, ge=0, le=100)
    pride: int = Field(default=50, ge=0, le=100) # Pride defaults to 50
    last_affection_update: Optional[datetime] = None
    last_anger_update: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_utc_now)
