import asyncio
from enum import Enum
import random
from typing import Optional
from ...exceptions import InGameException
from games.uno import acts, static
from models.gameplay import GameConfig, UnoConfig
from models.typs import Player
from .card import Card

class PlayerActs(Enum):
    THROW = "throw"
    TAKE = "take"
    UNO = "uno"
    GIVEUP = "giveup"
    CHECK = "check"

class UnoGame:
    __slots__ = (
        "players", "active_player", "clockwise_direction", "cfg", "processor_task", 
        "id","future", "not_said_uno", "current_card", "hands", "eliminated_players",
        "active_players", "running", "add_sum", "round", "next_winner_place",
        "next_loser_place", "cheated"
    )
    def __init__(self, cfg: GameConfig, id: str):
        if cfg.gameType != "Uno":
            raise InGameException("Invalid game type for UnoGame")
        elif not isinstance(cfg.specialConfig, UnoConfig):
            raise InGameException("Invalid game configuration for UnoGame")
        self.players: list[Player] = []
        self.active_players: list[Player] = []
        self.clockwise_direction = True
        self.cfg = cfg
        self.processor_task: asyncio.Task
        self.add_sum = 0
        self.future: Optional[asyncio.Future] = None
        self.cheated = False
        self.not_said_uno = set()
        self.current_card: Card
        self.hands: dict[Player, list[Card]] = {}
        self.eliminated_players: dict[Player, int] = {}
        self.id = id
        self.running: bool = False
        self.next_winner_place = 0
        self.next_loser_place = cfg.playersCount - 1
    
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
        self.active_player = random.choice(self.active_players)
        self.running = True
        self.round = 0
        self.future = asyncio.get_event_loop().create_future()
        self.processor_task = asyncio.create_task(self._processor())
    
    async def act(
        self,
        player: Player,
        action: PlayerActs,
        card: Optional[Card] = None
    ) -> None:
        if not self.running:
            raise InGameException("Game not started.")

        ACTIONS = {
            PlayerActs.THROW: (acts.throw, True),
            PlayerActs.TAKE: (acts.take, False),
            PlayerActs.UNO: (acts.uno, False),
            PlayerActs.GIVEUP: (acts.giveup, False),
            PlayerActs.CHECK: (acts.check, False),
        }

        try:
            handler, requires_card = ACTIONS[action]
        except KeyError:
            raise InGameException("Invalid action")

        if action == PlayerActs.THROW and self.active_player != player:
            raise InGameException("It's not your turn!")

        if requires_card and card is None:
            raise InGameException("Card must be provided for this action")

        if not requires_card and card is not None:
            raise InGameException("Card must not be provided for this action")
        arg = card if requires_card else player
        result = handler(self, arg)
        await self._update_future()
        return result
    
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

    async def _update_future(self):
        if self.future and not self.future.done():
            self.future.set_result(None)
        self.future = asyncio.get_event_loop().create_future()

    async def _processor(self):
        while self.running:
            try:
                if not self.future:
                    raise InGameException ("Processor called without a future")
                await asyncio.wait_for(self.future, timeout=
                                static.get_timeout_from_cfg(self)
                )
                await self._update_future()
            except asyncio.TimeoutError:
                await self.act(self.active_player, PlayerActs.TAKE)
                await self._update_future()