import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    bot_token: str
    bot_mode: str = "polling"
    api_base_url: str = "https://api.hunterstar.online"
    webapp_url: str = "https://hunterstar.online/"
    bot_username: str = "hunterstarfilebot"

    mongodb_uri: str

    r2_account_id: str = ""
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str
    r2_endpoint: str

    # Admin — explicitly a Telegram numeric user ID
    telegram_admin_user_id: int = Field(alias="admin", default=0)

    openrouter_api_key: str = ""

    # ── Venice AI (direct — NOT through OpenRouter) ──────────────────────────
    venice_api_key1: str = ""
    venice_api_key2: str = ""
    venice_api_key3: str = ""
    venice_api_key4: str = ""
    venice_api_key5: str = ""
    venice_api_key6: str = ""
    venice_base_url: str = "https://api.venice.ai/api/v1"
    venice_model: str = "llama-3.3-70b"
    # Number of requests each Venice API key may make per calendar day
    venice_daily_limit: int = 10

    # ── Firebase Admin SDK ───────────────────────────────────────────────────
    # Path to the service account JSON on the server — never commit the file itself
    firebase_credentials_path: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,   # allow both field name and alias
    )

    @property
    def admin(self) -> int:
        """Backward-compat alias so existing bot.py references keep working."""
        return self.telegram_admin_user_id

settings = Settings()
