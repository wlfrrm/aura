import random

from models.typs import Player

from ...games import Game
from .card import Ranks, Suits, Card

def get_passive_card() -> Card:
    suit = random.choice([Suits.Piki, Suits.Trefy, Suits.Chervi, Suits.Bubny])
    rank = random.randint(1, 10)
    return Card(suit=suit, rank=Ranks(rank))

def get_card() -> Card:
    token = random.randint(1, 100)
    if token <= 10:
        return Card(suit=Suits.Joker, rank=random.choice([Ranks.BlackJoker, Ranks.ColorfulJoker]))
    elif token <= 30:
        suit = random.choice([Suits.Piki, Suits.Trefy, Suits.Chervi, Suits.Bubny])
        rank = random.choice([Ranks.Jack, Ranks.Queen, Ranks.King])
        return Card(suit=suit, rank=rank)
    else:
        return get_passive_card()
    

def get_player(game: Game, player: Player, swift: int = -1) -> Player:
    game.players.index(player)
    return game.players[(game.players.index(player) + swift) % len(game.players)]