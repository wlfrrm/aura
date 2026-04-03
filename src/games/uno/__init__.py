from enum import Enum
import random
from typing import Literal, Optional
from ...exceptions import InGameException
from games.uno import acts, static
from models.gameplay import GameConfig
from models.typs import Player
from .card import Card, Ranks, Suits

class PlayerActs(Enum):
    THROW = "throw"
    TAKE = "take"
    UNO = "uno"
    CHECK = "check"

class UnoGame:
    __slots__ = (
        "players", "active_player", "clockwise_direction", "cfg", "processor_task", 
        "id","futures", "not_said_uno", "current_card", "hands", "eliminated_players",
        "active_players", "running", "add_sum", "round"
    )
    def __init__(self, cfg: GameConfig, id: str):
        if cfg.gameType != "Uno":
            raise InGameException("Invalid game type for UnoGame")
        self.players: list[Player] = []
        self.active_players: list[Player] = []
        self.active_player = random.choice(self.active_players)
        self.clockwise_direction = True
        self.cfg = cfg
        self.add_sum = 0
        self.processor_task = None
        self.futures = {}
        self.not_said_uno = set()
        self.current_card: Card
        self.hands: dict[Player, list[Card]] = {}
        self.eliminated_players = set()
        self.id = id
        self.running: bool = False
    
    # --- public methods ---

    def add_player(self, player: Player):
        if len(self.players) >= self.cfg.playersCount:
            raise InGameException("Maximum number of players reached")
        self.players.append(player)
        self.hands[player] = []
    
    def run(self):
        if len(self.players) < self.cfg.playersCount:
            raise InGameException("Not enough players to start the game")
        self._setup_hands()
        self.current_card = static.get_passive_card()
        self.active_players = self.players.copy()
        self.running = True
        self.round = 0
    
    def act(self, 
            player: Player, action: PlayerActs, 
            card: Optional[Card] = None) -> None:
        if player != self.active_player:
            raise InGameException("It's not your turn")
        if self.running != "active":
            raise InGameException("Game not started.")
        try:
            return {
                PlayerActs.THROW: acts.throw,
                PlayerActs.TAKE: acts.take,
                PlayerActs.UNO: acts.uno,
                PlayerActs.CHECK: acts.check
            }[action](self, card)
        except KeyError:
            raise InGameException("Invalid action")
    
    # --- bound methods ---

    def _move_to_next(self, block: bool):
        try:
            curindex = self.active_players.index(
                self.active_player
            )
        except ValueError:
            raise InGameException("Some Error in game...")
        self.active_player = self.active_players[
            (
                (curindex + 2 
                    if block else 1) % len(self.active_players)
            ) * 1 if self.clockwise_direction else -1
        ]

    def _end_round(self):
        self.round += 1

    def _setup_hands(self):
        for hand in self.hands.values():
            for _ in range(7):
                hand.append(static.get_card())

