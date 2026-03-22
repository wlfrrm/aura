import asyncio
from enum import Enum
from typing import Callable, Literal, Optional, Union
from ...models.enums import States
from ...models.typs import Player
from ...models.gameplay import DurakConfig, GameConfig
from ...connector import GameConn
from .card import Card, Ranks, Suits
import random as rd
from ...db import get_db

class PlayerActs(Enum):
    ATTACK = "ATTACK"
    THROW = "THROW"
    DEFEND = "DEFEND"
    GIVEUP = "GIVEUP"
    PASS = "PASS"
    CHECK = "CHECK"

class DurakGame():
    __slots__ = [
        "id", "cfg", "players", "hands", "table", "trump", 
        "deck", "state", "active_players", "eliminated",
        "conn", "attacker", "circle", "counter", "game_state",
        "futures", "processor_task", "passed_attackers", 
        "passed", "bringed"
        ]
        

    def __init__(self, config: GameConfig, id: str) -> None:
        if not isinstance(config.specialConfig, DurakConfig):
            raise ValueError("Пошел ка ты нахуй")
        self.game_state = States.NOT_STARTED
        self.cfg = config
        self.id = id
        self.bringed: bool = False
        self.players: list[Player] = []
        self.hands: dict[Player, list[Card]] = {}
        self.table: list[list[Card]] = []
        self.deck: list[Card] = []
        self.state: Literal["attacking", "throwing"] = "attacking"
        self.active_players: list[Player] = []
        self.attacker: Player
        self.eliminated: list[int] = []
        self.conn = GameConn()
        self.circle = 1
        self.passed: list[Player] = []
        self.counter = self._round_counter()
        self.futures: dict[Player, asyncio.Future] = {}
        self.passed_attackers: list[Player] = []
    
    async def add_player(self, pl: Player) -> bool:
        mn = await get_db().get_money(pl.id)
        if not mn:
            raise ValueError("Player is not exist")
        if mn < self._calc_exp():
            raise ValueError("You have no so credits")
        self.players.append(pl)
        return True

    def run(self) -> bool:
        if len(self.players) != self.cfg.playersCount:
            raise ValueError("Cannot start: players count is less than recognised in config.")
        self.active_players = self.players.copy()
        self.attacker = rd.choice(self.active_players)
        self.state = "attacking"
        self.game_state = States.GOING
        self._create_deck()
        self._deal_initial_hands()
        self.processor_task = asyncio.create_task(
            self._processor()
        )
        return True

    def act(self, acttype: PlayerActs,
            player: Player,
            slot: Optional[int], 
            card: Optional[Card]) -> None:
        if player not in self.active_players:
            raise ValueError("Player is not active in game.")
        match acttype:
            case PlayerActs.PASS:
                return self._pass(player)
            case PlayerActs.ATTACK:
                if not card:
                    raise ValueError("Card data need.")
                return self._attack(player, card)
            case _:
                raise ValueError("Unavaible action.")

    # actions

    def _attack(self, player: Player, card: Card) -> None:
        if player != self.attacker:
            raise ValueError("You dont attacker now.")
        if len(self.table) != 0:
            raise ValueError("Now throw stage, not attacking.")
        self._substract_card(player, card)
        self.table[0] = [card]
        self.futures[player].set_result(...)
        self.state = "throwing"
        self._create_future(player)
        self._create_future(self.defender)
        self._pass(player)

    def _pass(self, player: Player) -> None:
        if player == self.attacker:
            if player in self.passed_attackers:
                return self._giveup(player)
            self.passed_attackers.append(player)
            self._move_to_next_attacker()
            self._refill_hands()
        elif player == self.defender:
            if len(self.table) == 0:
                raise ValueError("Attacker is not attacked yet.")
            self.bringed = True
            
            self._setup_throwers()

        return


    def _giveup(self, player: Player) -> None:
        return

    def _throw(self, player: Player, card: Card) -> None:
        return

    def _defend(self, player: Player, card: Card) -> None:
        return

    # bound

    @property
    def defender(self) -> Player:
        return self._get_player(
            self.attacker,
            1 # next
        )

    def _can_beat(self, old: Card, new: Card, trump: Suits):
        if Suits.Joker in (old.suit, new.suit):
            return True
        if old.suit == new.suit:
            return new.rank > old.rank
        return new.suit == trump and old.suit != trump

    def _calc_exp(self) -> int | float:
        if self.cfg.betType == "all-in":
            return self.cfg.gameBet + 0.1 * self.cfg.gameBet
        else:
            return round(self.cfg.gameBet / self.cfg.playersCount + 0.1 * self.cfg.gameBet)

    def _get_player(self, pl: Player, shift: int) -> Player:
        if not self.active_players:
            raise RuntimeError("Game is ended.")

        try:
            i = self.active_players.index(pl)
        except ValueError:
            raise RuntimeError("Player is not in game")

        return self.active_players[(i + shift) % len(self.active_players)]
    
    def _round_counter(self) -> Callable[[], None]:
        counter = 0

        def _():
            nonlocal counter

            players_count = len(self.active_players)
            if players_count == 0:
                return

            counter += 1

            if counter >= players_count:
                self.circle += 1
                counter = 0

        return _

    def _create_deck(self) -> list[Card]:
        deck: list[Card] = []
        if not isinstance(self.cfg.specialConfig, DurakConfig):
            raise ValueError("Пошел ка ты нахуй")
        if self.cfg.specialConfig.cardsCount == 24:
            ranks_range = [Ranks.Nine, Ranks.Ten, Ranks.Jack, Ranks.Queen, Ranks.King, Ranks.Ace]
        elif self.cfg.specialConfig.cardsCount == 36:
            ranks_range = [Ranks.Six, Ranks.Seven, Ranks.Eight, Ranks.Nine, Ranks.Ten,
                        Ranks.Jack, Ranks.Queen, Ranks.King, Ranks.Ace]
        elif self.cfg.specialConfig.cardsCount == 52:
            ranks_range = [Ranks.Two, Ranks.Three, Ranks.Four, Ranks.Five, Ranks.Six, Ranks.Seven,
                        Ranks.Eight, Ranks.Nine, Ranks.Ten, Ranks.Jack, Ranks.Queen, Ranks.King, Ranks.Ace]
        else:
            raise ValueError(f"Unsupported cards count: {self.cfg.specialConfig.cardsCount}")

        for suit in [Suits.Piki, Suits.Trefy, Suits.Chervi, Suits.Bubny]:
            for rank in ranks_range:
                deck.append(Card(suit=suit, rank=rank))

        if self.cfg.specialConfig.jokers:
            deck.append(Card(suit=Suits.Joker, rank=Ranks.Joker))
            deck.append(Card(suit=Suits.Joker, rank=Ranks.Joker))

        rd.shuffle(deck)

        self.deck = deck
        return deck

    def _refill_hands(self) -> None:
        if not isinstance(self.cfg.specialConfig, DurakConfig):
            raise ValueError("Пошел ка ты нахуй")
        if not self.deck:
            return

        max_cards = self.cfg.specialConfig.cardsCount // len(self.players)

        # создаём очередь игроков начиная с атакующего
        queue = [self.attacker] + [self._get_player(self.attacker, i) for i in range(1, len(self.active_players))]

        for pl in queue:
            hand = self.hands[pl]
            missing = max_cards - len(hand)
            if missing <= 0:
                continue

            draw = self.deck[:missing]
            hand.extend(draw)
            self.deck = self.deck[missing:]

    def _deal_initial_hands(self) -> None:
        # создаём словарь Player -> пустая рука
        self.hands = {pl: [] for pl in self.active_players}
        max_cards = self.cfg.specialConfig.cardsCount // len(self.players)  # type: ignore

        while any(len(hand) < max_cards for hand in self.hands.values()) and self.deck:
            for pl, hand in self.hands.items():
                if len(hand) < max_cards and self.deck:
                    hand.append(self.deck.pop(0))

    def _substract_card(self, player: Player, card: Card) -> None:
        try:
            self.hands[player].remove(card)
        except ValueError:
            raise ValueError("You dont have this card.")

    def _move_to_next_attacker(self):
        self.attacker = self._get_player(self.attacker, self.bringed + 1)
# self.bringed + 1 => 2 if True and 1 if False, coz int(True) = 1, an. False => 0
        self.bringed = False
        self.counter()

    async def _wait_future(self, player: Player):
        try:
            fut = self.futures.get(player)
            if not fut:
                raise ValueError("Player has no active actions.")
            await asyncio.wait_for(fut, 
                (6 if self.cfg.speed == "Rapid" else
                (15 if self.cfg.speed == "Fast" else 30))
            )
        except asyncio.TimeoutError:
            self._pass(player)
        del self.futures[player]

    def _create_future(self, player: Player):
        self.futures[player] = asyncio.get_event_loop().create_future()

    async def _processor(self):
        while self.game_state == States.GOING:
            for pl in self.futures.keys():
                asyncio.create_task(
                    self._wait_future(pl)
                )

    def _setup_throwers(self):
        match self.cfg.specialConfig.throwing:
            case "all":
                pls = self.players.copy()
                try:
                    pls.remove(self.attacker)
                    pls.remove(self.defender)
                except ValueError:
                    raise ValueError("game is fatal broken.")
                for pl in pls:
                    self._create_future(pl)
            case "next-pervious-only":
                self._create_future(self.attacker)
                self._create_future(
                    self._get_player(self.defender, 1)
                )
            case _:
                raise ValueError("cho blyat, game is fatal broken.")