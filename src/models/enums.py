from enum import IntEnum, StrEnum

class GameTypes(StrEnum):
    Durak = "Durak"
    Uno = "Uno"
    

class GameSpeeds(StrEnum):
    Normal = "Normal"
    Fast = "Fast"
    Rapid = "Rapid"

class GameBetType(StrEnum):
    Deal = "deal"
    AllIn = "all-in"
    WinAll = "win-all"

class States(StrEnum):
    """Game-level states."""
    NOT_STARTED = "NOT_STARTED"
    GOING = "GOING"
    ENDED = "ENDED"