import os
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
    admin: int
    openrouter_api_key: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
