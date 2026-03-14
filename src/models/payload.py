from pydantic import BaseModel
from .typs import LoginData
from .gameplay import GameConfig

class _model(BaseModel):
    loginData: LoginData

class CreateGame(_model):
    gameConfig: GameConfig