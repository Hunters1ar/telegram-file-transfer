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
    created_at: datetime = Field(default_factory=get_utc_now)
