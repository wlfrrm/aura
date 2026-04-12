from typing import TYPE_CHECKING
from models.typs import Player
from models.gameplay import UnoConfig
from . import InGameException, static
from games.uno.card import Card, Effects, Ranks, Suits
if TYPE_CHECKING:
    from . import UnoGame

def throw(self: UnoGame, card: Card) -> None:
    if not self.current_card.covers_by(card):
        if self.cfg.cheater:
            self.cheated = True
        else:
            raise InGameException("Incorrect Card!")
    if self.add_sum > 0:
        if card.effect != Effects.PLUS: 
            raise InGameException("You must take cards or throw a plus card!")
    if card.effect:
        if card.effect == Effects.BLOCK:
            self._move_to_next(block=True)
        elif card.effect == Effects.REVERSE:
            self.clockwise_direction = not self.clockwise_direction
        elif card.effect == Effects.PLUS:
            self.add_sum += 2 if card.rank == 12 else 4
    if card not in self.hands[self.active_player]:
        raise InGameException("You don't have this card!")
    player = self.active_player
    self.current_card = card
    self.hands[player].remove(card)
    if len(self.hands[player]) == 0:
        static.eliminate_winner(self, player)
    else:
        static.mark_uno_if_needed(self, player)
        self._move_to_next(False)

def take(self: UnoGame, card: None = None) -> None:
    if not isinstance(self.cfg.specialConfig, UnoConfig):
        raise InGameException("Invalid game configuration for UnoGame")
    player = self.active_player
    if self.cfg.specialConfig.takingRule == "while-cant-beat":
        while not any(card.covers_by(self.current_card) for card in self.hands[player]):
            self.hands[player].append(static.get_card())
    else:
        cards_to_take = self.add_sum if self.add_sum > 0 else (2 if self.cfg.specialConfig.takingRule == "two" else 1)
        for _ in range(cards_to_take):
            self.hands[player].append(static.get_card())
    self.add_sum = 0
    static.mark_uno_if_needed(self, player)
    self._move_to_next(False)

def uno(self: UnoGame, player: Player) -> None:
    had_own_uno = player in self.not_said_uno
    if had_own_uno:
        self.not_said_uno.discard(player)

    punished_count = static.punish_not_said_uno(self, excluded_player=player)
    if had_own_uno or punished_count > 0:
        return

    for _ in range(self.cfg.specialConfig.takingIfNotUno):  # pyright: ignore[reportAttributeAccessIssue]
        self.hands[player].append(static.get_card())

def giveup(self: UnoGame, player: Player) -> None:
    static.eliminate_giveup(self, player)

def check(self: UnoGame, player: Player) -> None:
    if not self.cfg.cheater:
        raise InGameException("Cheater mode is disabled!") 
    if self.cheated:
        return giveup(self, static.get_player(self, self.active_player, -1))
    else:
        return giveup(self, player)