from collections.abc import Iterable
from typing import Optional
from .games import Game
from .utils import random_base62

class Allocator():
    __slots__ = ["allocated"]
    def __init__(self) -> None:
        self.allocated = {}

    def push(self, game: Game): #type:ignore
        self.allocated[game.id] = game
    
    def get(self, id: str) -> Optional[Game]:
        game = self.allocated.get(id)
        if not game:
            return None
        return game

    def search(self, filters: dict[str, str | int]) -> Iterable[Game]:
        for game in self.allocated.values():
            if all(getattr(game, k) == v for k, v in filters.items()):
                yield game

    @property
    def new_key(self) -> str:
        while True:
            key = random_base62()
            if self.get(key):
                continue
            return key
