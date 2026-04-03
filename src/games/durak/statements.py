from enum import Enum
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from asyncio import Future

class PlayerActs(Enum):
    ATTACK = "ATTACK"
    THROW = "THROW"
    DEFEND = "DEFEND"
    GIVEUP = "GIVEUP"
    PASS = "PASS"
    CHECK = "CHECK"

def cb(fut: Future):
    if fut.cancelled():
        pass  # Ожидаемое поведение - фьючерс был отменён
    elif fut.exception():
        print("Task failed:", fut.exception())
    else:
        print("Oke.")