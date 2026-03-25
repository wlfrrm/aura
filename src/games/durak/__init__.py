import asyncio
from enum import Enum
from typing import Any, Callable, Literal, Optional, Union
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
        "passed", "bringed", "procfuture", "_waiting", "cheaters"
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
        self.cheaters: set[Player] = set()
        self.trump = Suits.Joker
    
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
        self.procfuture = asyncio.get_event_loop().create_future()
        self.game_state = States.GOING
        self._create_deck()
        self._deal_initial_hands()
        try:
            while self.trump == Suits.Joker:
                for n in range(1, 4):
                    self.trump = self.deck[-n]
        except IndexError:
            self.trump = rd.choice([Suits.Bubny, Suits.Chervi, Suits.Piki, Suits.Trefy])
        self.processor_task = asyncio.create_task(
            self._processor()
        )
        return True

    def act(self, acttype: PlayerActs,
            player: Player,
            slot: Optional[int], 
            card: Optional[Card]) -> None:
        self.ping_proc()
        if player not in self.active_players:
            raise ValueError("Player is not active in game.")
        match acttype:
            case PlayerActs.PASS:
                self._pass(player)
            case PlayerActs.ATTACK:
                if not card:
                    raise ValueError("Card data need.")
                self._attack(player, card)
            case PlayerActs.THROW:
                if not card:
                    raise ValueError("Card data need.")
                self._throw(player, card)
            case PlayerActs.DEFEND:
                if not card:
                    raise ValueError("Card data need.")
                if not slot:
                    raise ValueError("Slot data need.")
                self._defend(player, slot, card)
            case PlayerActs.CHECK:
                if PlayerActs.CHECK not in self._avaible_actions(player):
                    raise ValueError("Cannot CHECK now")
                self._check(player)
            case PlayerActs.GIVEUP:
                self._giveup(player)
            case _:
                raise ValueError("Unavaible action.")
        self.ping_proc()

    # --- actions ---

    def _attack(self, player: Player, card: Card) -> None:
        if player != self.attacker:
            raise ValueError("You are not attacker now.")
        if self.state != "attacking":
            raise ValueError("Cannot attack during throw phase.")
        if card not in self.hands.get(player, []):
            raise ValueError("You do not have this card.")

        if not self.table:
            self.table.append([])

        self.hands[player].remove(card)
        self.table[0].append(card)
        self.state = "throwing"

        # Создаём фьючерсы для защиты и повторного хода
        for p in [self.defender, player]:
            if p not in self.futures or self.futures[p].done():
                self._create_future(p)

    def _pass(self, player: Player) -> None:
        if player == self.attacker:
            if player in self.passed_attackers:
                self._giveup(player)
                return
            self.passed_attackers.append(player)
            self._move_to_next_attacker()
            self._refill_hands()
            return

        if player == self.defender:
            if not self.table:
                raise ValueError("Attacker is not attacked yet.")
            self.bringed = True
            self.passed.append(player)

            if player in self.futures:
                self.futures[player].set_result(...)
                del self.futures[player]

            for pl in self.active_players:
                if pl != self.defender and pl not in self.passed and pl not in self.futures:
                    self._create_future(pl)

            if all(pl in self.passed for pl in self.active_players if pl != self.defender):
                self._setup_throwers()
            return

        if self.state == "throwing" and player in self.futures:
            self.passed.append(player)
            self.futures[player].set_result(...)
            del self.futures[player]

            if all(pl in self.passed for pl in self.active_players if pl != self.defender):
                self._setup_throwers()
            return

    def _giveup(self, player: Player) -> None:
        if player not in self.hands:
            return

        for pile in self.table:
            self.hands[player].extend(pile)

        self.table.clear()
        self.bringed = False
        self.passed.clear()
        self.passed_attackers.clear()

        self._move_to_next_attacker()
        self._refill_hands()

    def _throw(self, player: Player, card: Card) -> None:
        if self.state != "throwing":
            raise ValueError("Not throw phase.")
        if player == self.defender:
            raise ValueError("Defender cannot throw.")
        if card not in self.hands.get(player, []):
            raise ValueError("You do not have this card.")
        max_throw = min(5 if self.circle == 1 else 6, len(self.hands[self.defender]))
        if sum(len(pile)-1 for pile in self.table) >= max_throw:
            raise ValueError("Too many cards thrown this round.")
        if not self._check_throw_rank(card.rank):
            raise ValueError("You cannot throw this card.")
        self.table.append([card])
        self.hands[player].remove(card)
        
    def _defend(self, player: Player, slot: int, card: Card) -> None:
        if player != self.defender:
            raise ValueError("Only defender can defend now.")
        try:
            pile = self.table[slot]
        except IndexError:
            raise ValueError("pile is not exist")
        if len(pile) == 1: 
            top_card = pile[0]
            if not self._can_beat(top_card, card):
                if self.cfg.cheater:
                    self.cheaters.add(player)
                else:
                    raise ValueError("Cannot beat with this card.")
            self.hands[player].remove(card)
            pile.append(card)
            if player in self.futures and not self.futures[player].done():
                self.futures[player].set_result(...)
                del self.futures[player]
            if all(len(pile) == 2 for pile in self.table):
                self._end_round()
            return
        raise ValueError("No card to defend or cannot beat any.")

    def _check(self, player: Player):
        if self.cheaters:
            for cheater in self.cheaters:   
                self._giveup(cheater)
        else:
            self._giveup(player)
    
    def _setup_throwers(self):
        self.state = "attacking"
        self.passed.clear()
        self.bringed = False

        self.attacker = self._get_player(self.attacker, 1)

        if self.attacker not in self.futures:
            self._create_future(self.attacker)
        if self.defender not in self.futures:
            self._create_future(self.defender)

    # bound

    @property
    def defender(self) -> Player:
        return self._get_player(
            self.attacker,
            1 # next
        )

    @property
    def _attacker_passed(self) -> bool:
        return self.attacker in self.passed

    @property
    def _last_card(self) -> Optional[Card]:
        try:
            return self.deck[-1]
        except IndexError:
            return None

    def _avaible_actions(self, player: Player) -> list[PlayerActs]:
        # Игроки, которые уже пропустили ход, могут только сдаться
        if player in self.passed:
            return [PlayerActs.GIVEUP]

        result: list[PlayerActs] = []

        # Защитник может отбиваться
        if player == self.defender and self.table:
            result.append(PlayerActs.DEFEND)
            result.append(PlayerActs.PASS)

        # Атакующий на стадии атаки
        if player == self.attacker and self.state == "attacking":
            if self.hands.get(player):
                result.append(PlayerActs.ATTACK)
            result.append(PlayerActs.PASS)

        # Игроки на стадии "throwing" могут подкидывать карты
        if self.state == "throwing" and player != self.defender:
            if self.hands.get(player) and self.cfg.specialConfig.throwing == "all":
                result.append(PlayerActs.THROW)
                result.append(PlayerActs.PASS)
            elif self.hands.get(player) and self.cfg.specialConfig.throwing == "next-pervious-only":
                # Игрок может подкидывать если он "следующий" или уже участвовал
                if player in self.passed or player == self._get_player(self.attacker, 1):
                    result.append(PlayerActs.THROW)
                    result.append(PlayerActs.PASS)

        # Действие "CHECK" доступно только если включен шуллер и есть карты на столе
        if self.cfg.cheater and self.table:
            result.append(PlayerActs.CHECK)

        return result

    def _can_beat(self, old: Card, new: Card):
        if Suits.Joker in (old.suit, new.suit):
            return True
        if old.suit == new.suit:
            return new.rank > old.rank
        return new.suit == self.trump and old.suit != self.trump

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

    def _check_throw_rank(self, rank: Ranks) -> bool:
        for pile in self.table:
            for card in pile:
                if card.rank == rank:
                    return True
        return False
    
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
        self.ping_proc()

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
        self.ping_proc()

    def _end_round(self):
        self.table.clear()
        self.passed.clear()
        self.passed_attackers.clear()
        self._move_to_next_attacker()
        self._refill_hands()
        self.cheaters.clear()

    async def _wait_future(self, player: Player):
        if player in self._waiting:
            return
        self._waiting.add(player)
        fut = self.futures.get(player)
        if not fut:
            self._waiting.discard(player)
            return

        timeout = 6 if self.cfg.speed == "Rapid" else 15 if self.cfg.speed == "Fast" else 30
        try:
            await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            self._pass(player)
        finally:
            if self.futures.get(player) is fut:
                del self.futures[player]
            self._waiting.discard(player)

    def _create_future(self, player: Player):
        if player in self.futures:
            fut = self.futures[player]
            if fut.done():
                self.futures[player] = asyncio.get_event_loop().create_future()
        else:
            self.futures[player] = asyncio.get_event_loop().create_future()

    async def _processor(self):
        while self.game_state == States.GOING:
            if not hasattr(self, "_waiting"):
                self._waiting = set()

            for pl in tuple(self.futures.keys()):
                if pl not in self._waiting:
                    self._waiting.add(pl)
                    asyncio.create_task(self._wait_future(pl))
            try:
                await asyncio.wait_for(self.procfuture, 3)
            except asyncio.TimeoutError:
                self.ping_proc()

    def ping_proc(self): # anti pooling system
        try:
            self.procfuture.set_result(...)
        except asyncio.InvalidStateError:
            pass
        finally:
            self.procfuture = asyncio.get_event_loop().create_future()

    def serialize(self, player: Player) -> dict[str, Any]:
        return {
            "state": self.state,
            "table": self.table,
            "hand": self.hands[player],
            "trump": self.trump,
            "last_card": self._last_card,
            "attacker": self.attacker,
            "defender": self.defender,
            "avaible_actions": self._avaible_actions(player),
            "players": {pl.id: {
                "frame": pl.frame,
                "backcard": pl.backcard,
                "ingame": pl in self.active_players,
                "cards": len(self.hands[pl]),
                "php": pl.phplink,
                "name": pl.name
            } for pl in self.players}
        }