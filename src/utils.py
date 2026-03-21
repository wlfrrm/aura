import hmac
import hashlib
from typing import Dict
from .config import Config
import random as rd

def check_webapp_hash(data: Dict[str, str]) -> bool:
    """Validate Telegram WebApp data using server-side bot token"""
    hash_to_check = data.pop("hash", None)
    if not hash_to_check:
        return False
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(Config.BOT_TOKEN.encode()).digest()  # токен берём из Config
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return hmac_hash == hash_to_check

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def random_base62(min_len=7, max_len=14) -> str:
    length = rd.randint(min_len, max_len)
    return ''.join(rd.choices(BASE62, k=length))