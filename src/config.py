from pydantic import BaseModel
from typing import List
import json
import tomli

class _Config(BaseModel):
    RATING_COEF: float
    CREDIT_COMM: float
    DAILY_CREDIT: int
    STD_EMOJIS: List[int]
    STD_ELO: int
    DEFAULT_CREDIT: int
    DEFAULT_GOLD: int
    ENABLED_GAMES: List[str]
    NEW_REGISTARTIONS: bool
    LOG_FILE: str
    TEST_MODE: bool
    DATABASE_FILE: str
    LEAGUE_COEF: float
    BOT_TOKEN: str
    HOST: str
    PORT: int
    TIMEOUT_RAPID: int
    TIMEOUT_STANDARD: int
    TIMEOUT_FAST: int

    @classmethod
    def from_json_file(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def from_toml_file(cls, path: str):
        with open(path, "rb") as f:  # tomli читает только байты
            data = tomli.load(f)
        # Если есть секции, распаковываем [constants] напримерs
        if "constants" in data:
            data = data["constants"]
        return cls(**data)
    

Config = _Config.from_toml_file("conf[exm].toml")