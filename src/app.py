import fastapi as fa
from aiogram import Bot, Dispatcher
import pydantic as pd
from .config import Config
from .db import get_db
from .models import (LoginData, Player, WebAppData, 
                    TempLoginData, CreateGame)
from .alloc import Allocator

alloc = Allocator()
api = fa.FastAPI(docs_url=None, redoc_url=None, debug=Config.TEST_MODE)
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

@api.exception_handler(ValueError)
async def value_error(req: fa.Request, exc: ValueError):
    raise fa.HTTPException(
        422,
        f"value or some values is incorrect: {exc.args}",
    )

@api.get("/")
async def html_give():
    html = ""
    return fa.responses.HTMLResponse(html)

@api.get("/js")
async def script_give():
    script = ""
    return fa.responses.HTMLResponse(script)

@api.post("/getMe")
async def get_me(login: LoginData):
    try:
        if login.type == "WebApp":
            web_data: WebAppData = login.raw  # уже валидировано # type: ignore[assignment]
            user_id = web_data.id
            name = f"{web_data.first_name or ''} {web_data.last_name or ''}".strip()
            php = "/anonim.webp"  # можно расширить, если есть URL
        else:  # TempLogin
            temp_data: TempLoginData = login.raw # уже валидировано # type: ignore[assignment]
            user_id = temp_data.id
            name = temp_data.fullname or ""
            php = temp_data.php or "/anonim.webp"

        usr = await get_db().get_or_create_user(user_id, php)

        return dict(
            id=user_id,
            name=name,
            gold=usr.gold,
            money=usr.money,
            elo=usr.elo,
            login_data=login,
            php=php
        )

    except Exception as e:
        # если Pydantic кинул ValidationError — поймаем здесь
        raise fa.HTTPException(status_code=403, detail=f"Invalid login data: {str(e)}")

@api.get("/getPlayer")
async def get_player(id: int) -> Player:
    """
    Получает информацию об игроке по ID.
    """
    usr = await get_db().get_user(id)
    if not usr:
        raise fa.HTTPException(status_code=404, detail="Player not found")
    return Player(
        id=usr.id,
        name=usr.name,
        elo=usr.elo,
        phplink=usr.phplink
    )

@api.post("/gameApi/new")
async def new_game(data: CreateGame):
    gconfig = data.gameConfig
    
    return 

@api.websocket("/gameApi/connect")
async def connect_game(ws: fa.WebSocket, id: str):
    game = alloc.get(id) # now returns None if game is not exist.
    if not game:
        raise fa.WebSocketException(404, "Game is not exist.")
    await ws.accept()
    try:
        raw_login: pd.JsonValue = await ws.receive_json()
        try:
            login_data: LoginData = LoginData.model_validate(raw_login)
        except pd.ValidationError:
            await ws.close(1008, "пошел нахуй чмо")
            return
        while True:
            data: pd.JsonValue = await ws.receive_json()
            f"some actions with {data}"
    except fa.WebSocketDisconnect:
        pass