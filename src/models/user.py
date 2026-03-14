from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List

class User(BaseModel):
    id: int
    elo: int
    money: int
    gold: int
    phplink: str
    items: List[str]
    extra_emojis: List[str]
    wins: int
    draws: int
    losses: int
    games: int
    rating: int
    league_points: int
    selected_backcard: int
    selected_frame: int
    selected_emojis: List[str]
    registered_at: datetime
    last_game_at: datetime
    name: str
    
    @field_validator('selected_emojis', mode='before')
    @classmethod
    def convert_emojis_to_strings(cls, v):
        if isinstance(v, list):
            return [str(emoji) for emoji in v]
        return v
