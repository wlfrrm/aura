from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any, Literal
from ..utils import check_webapp_hash
from ..config import Config
import hashlib
import hmac

class Player(BaseModel):
    id: int
    name: str
    phplink: str
    elo: int
    frame: str = "f0"
    backcard: str = "c0"

class WebAppData(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    init_data: Dict[str, str]

    @model_validator(mode="before")
    def validate_webapp(cls, values):
        init_data = values.get("init_data")
        if not init_data:
            raise ValueError("init_data missing")
        if not check_webapp_hash(init_data.copy()):
            raise ValueError("WebApp data signature invalid")
        return values

class TempLoginData(BaseModel):
    id: int
    fullname: Optional[str]
    php: Optional[str]
    raw: Dict[str, Any]

    @model_validator(mode="after")
    def validate_templogin(self):
        data = self.raw.copy()

        hash_ = data.pop("hash", None)
        if not hash_:
            raise ValueError("No hash")

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(data.items())
        )

        secret = hashlib.sha256(Config.BOT_TOKEN.encode()).digest()

        check_hash = hmac.new(
            secret,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if check_hash != hash_:
            raise ValueError("Invalid telegram auth")

        return self

class LoginData(BaseModel):
    type: Literal["WebApp", "TempLogin"]
    raw: WebAppData | TempLoginData