from pydantic import BaseModel
from enum import IntEnum, StrEnum

class Suits(StrEnum):
    Piki = "Piki"
    Trefy = "Trefy"
    Chervi = "Chervi"
    Bubny = "Bubny"
    Joker = "Joker"

class Ranks(IntEnum):
    Ace = 14
    Two = 2
    Three = 3
    Four = 4
    Five = 5
    Six = 6
    Seven = 7
    Eight = 8
    Nine = 9
    Ten = 10
    Jack = 11
    Queen = 12
    King = 13
    Joker = 15

class Card(BaseModel):
    suit: Suits
    rank: Ranks

    def __str__(self):
        return f"{self.rank.name} of {self.suit.name}"
