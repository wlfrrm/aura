import fastapi as fa
import pydantic as pd

class GameConn:
    __slots__ = ["sockets"]
    def __init__(self) -> None:
        self.sockets: dict[int, fa.WebSocket] = {}
    
    def alloc(self, ws: fa.WebSocket, plid: int):
        self.sockets[plid] = ws
    
    async def send(self, id: int, dat: pd.JsonValue) -> None:
        try: 
            ws = self.sockets.get(id)
            if not ws:
                return
            await ws.send_json(dat)
        except ( RuntimeError, fa.WebSocketDisconnect ):
            pass

    