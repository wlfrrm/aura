from typing import TYPE_CHECKING, Optional, Self
from . import InGameException
from games.uno.card import Card, Effects, Suits
if TYPE_CHECKING:
    from . import UnoGame


def throw(self: UnoGame, card: Card) -> None:
    if not self.current_card.covers_by(card):
        raise InGameException("Incorrect Card!")
    if card.effect:
        if card.effect == Effects.BLOCK:
            self._move_to_next(block=True)
        elif card.effect == Effects.REVERSE:
            self.clockwise_direction = not self.clockwise_direction
        if card.effect == Effects.PLUS:
            self.add_sum += 2 if card.rank == 12 else 4
    self.current_card = card

def take(self: UnoGame, card: None = None) -> None:
    pass

def uno(self: UnoGame, card: None = None) -> None:
    pass

def check(self: UnoGame, card: None = None) -> None:
    pass