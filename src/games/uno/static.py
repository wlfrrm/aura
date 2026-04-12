import random

from models.typs import Player
from typing import TYPE_CHECKING
from ...exceptions import InGameException

from . import UnoGame as Game
from .card import Card, Ranks, Suits
from ...models import UnoConfig
if TYPE_CHECKING:
    from . import UnoGame

def get_passive_card() -> Card:
    suit = random.choice([Suits.Piki, Suits.Trefy, Suits.Chervi, Suits.Bubny])
    rank = random.randint(1, 10)
    return Card(suit=suit, rank=Ranks(rank))


def get_card() -> Card:
    token = random.randint(1, 100)
    if token <= 10:
        return Card(suit=Suits.Joker, rank=random.choice([Ranks.BlackJoker, Ranks.ColorfulJoker]))
    if token <= 30:
        suit = random.choice([Suits.Piki, Suits.Trefy, Suits.Chervi, Suits.Bubny])
        rank = random.choice([Ranks.Jack, Ranks.Queen, Ranks.King])
        return Card(suit=suit, rank=rank)
    return get_passive_card()


def get_player(game: Game, player: Player, swift: int = -1) -> Player:
    game.players.index(player)
    return game.players[(game.players.index(player) + swift) % len(game.players)]


def _set_place(game: Game, player: Player, place: int) -> None:
    if player not in game.eliminated_players:
        game.eliminated_players[player] = place


def _finish_if_needed(game: Game) -> None:
    if len(game.active_players) != 1:
        if not game.active_players:
            game.running = False
        return

    last_player = game.active_players[0]
    _set_place(game, last_player, game.next_winner_place)
    game.next_winner_place += 1
    game.active_players.clear()
    game.not_said_uno.discard(last_player)
    game.running = False


def eliminate_winner(game: Game, player: Player) -> None:
    _set_place(game, player, game.next_winner_place)
    game.next_winner_place += 1

    if player == game.active_player and len(game.active_players) > 1:
        game._move_to_next(False)

    if player in game.active_players:
        game.active_players.remove(player)

    game.not_said_uno.discard(player)
    _finish_if_needed(game)


def eliminate_giveup(game: Game, player: Player) -> None:
    _set_place(game, player, game.next_loser_place)
    game.next_loser_place -= 1

    if player == game.active_player and len(game.active_players) > 1:
        game._move_to_next(False)

    if player in game.active_players:
        game.active_players.remove(player)

    game.not_said_uno.discard(player)
    _finish_if_needed(game)

def mark_uno_if_needed(self: UnoGame, player) -> None:
    if len(self.hands[player]) == 1:
        self.not_said_uno.add(player)
    else:
        self.not_said_uno.discard(player)

def punish_not_said_uno(self: UnoGame, excluded_player=None) -> int:
    if not isinstance(self.cfg.specialConfig, UnoConfig):
        raise InGameException("Invalid game configuration for UnoGame")

    punished_players = [player for player in self.not_said_uno if player != excluded_player]
    penalty = self.cfg.specialConfig.takingIfNotUno

    for player in punished_players:
        for _ in range(penalty):
            self.hands[player].append(get_card())

    for player in punished_players:
        self.not_said_uno.discard(player)

    return len(punished_players)
