from typing import Literal, Union
from pydantic import BaseModel, validator, root_validator
from .enums import GameSpeeds, GameTypes, GameBetType

class DurakConfig(BaseModel):
    specialType: Literal["throw-in", "turnover"]
    jokers: bool
    throwing: Literal["all", "next-pervious-only"]
    cardsCount: int
    draws: bool

    @validator("cardsCount")
    def cards_count(cls, v: int) -> int:
        if v not in (24, 36, 52):
            raise ValueError("you cannot set this card count!")
        return v

class UnoConfig(BaseModel):
    takingRule: Literal["one", "two", "while-cant-beat"]
    takingIfNotUno: Literal[2, 4]

class GameConfig(BaseModel):
    gameType: GameTypes
    playersCount: int
    isPrivate: bool
    speed: GameSpeeds
    specialConfig: Union[DurakConfig, UnoConfig]
    gameBet: int
    draw: bool
    cheater: bool
    betType: GameBetType

    class Config:
        # required when using root_validator with pre=False in Pydantic v1
        validate_all = True

    @validator("playersCount", "gameBet")
    def non_negative(cls, v: int) -> int:  # pylint: disable=unused-argument
        if v < 0:
            raise ValueError   ("must be non-negative")
        return v

    @root_validator(pre=False, skip_on_failure=True)  # type: ignore[misc]
    def check_special_config_matches_type(cls, values):
        gt = values.get("gameType")
        sc = values.get("specialConfig")
        if gt == GameTypes.Durak and not isinstance(sc, DurakConfig):
            raise ValueError("specialConfig must be DurakConfig when gameType is Durak")
        if gt == GameTypes.Uno and not isinstance(sc, UnoConfig):
            raise ValueError("specialConfig must be UnoConfig when gameType is Uno")
        return values

