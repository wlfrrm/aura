from typing import Optional
from pydantic import BaseModel
from enum import IntEnum, StrEnum

class Effects(IntEnum):
    REVERSE = 0
    BLOCK = 1
    PLUS = 2

class Suits(StrEnum):
    Piki = "Piki"
    Trefy = "Trefy"
    Chervi = "Chervi"
    Bubny = "Bubny"
    Joker = "Joker"

class Ranks(IntEnum):
    Ace = 1
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
    BlackJoker = 15
    ColorfulJoker = 16

class Card(BaseModel):
    suit: Suits
    rank: Ranks

    def covers_by(self, card: "Card") -> bool:
        return (card.suit == self.suit or 
                self.rank == card.rank or 
                card.rank in (Ranks.BlackJoker, Ranks.ColorfulJoker)
            )
    
    def hand_has(self, hand: list["Card"]) -> bool:
        if self.rank in (Ranks.BlackJoker, Ranks.ColorfulJoker): # joker card can get any suit, so we check only rank
            return any(card.rank == self.rank for card in hand)
        return any(card.suit == self.suit and card.rank == self.rank for card in hand)

    @property
    def effect(self) -> Optional[Effects]:
        if self.rank in (Ranks.Queen, Ranks.ColorfulJoker):
            return Effects.PLUS
        if self.rank == Ranks.Jack:
            return Effects.REVERSE
        if self.rank == Ranks.King:
            return Effects.BLOCK
    
    def __str__(self):
        return f"{self.rank.name} of {self.suit.name}"
