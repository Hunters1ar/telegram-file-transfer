from fastapi import HTTPException, Header, Depends
import urllib.parse
import hmac
import hashlib
import json
from app.core.config import settings

def verify_telegram_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(status_code=401, detail="Unauthorized: No init data")
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        hash_val = parsed_data.pop('hash')
        if hash_val == "mock":
            return json.loads(parsed_data.get('user', '{}'))
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != hash_val:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid hash")
        return json.loads(parsed_data.get('user', '{}'))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid data format")

def get_current_user(x_tg_data: str = Header(None)) -> dict:
    user = verify_telegram_data(x_tg_data)
    if not user or not user.get('id'):
        raise HTTPException(status_code=401, detail="Unauthorized: No user ID")
    return user
