from aiosqlite import connect, Row
from .config import Config
from .models.user import User
import json

class QUERIES:
    get_user = "SELECT * FROM users WHERE id = ?"
    insert_user = """INSERT INTO users (id, elo, money, gold, phplink, selected_emojis, name) VALUES (?, ?, ?, ?, ?, ?, ?)"""
    add_money = "UPDATE users SET money = money + ? WHERE id = ?"
    get_money = "SELECT money FROM users WHERE id = ?"

class Database: # temp variant with sqlite3, will be replaced with postgres in the future
    def __init__(self, config = Config, queries = QUERIES):
        self.path = config.DATABASE_FILE
        self.q = queries
    
    async def do(self, query: str, *args):
        async with connect(self.path) as db:
            await db.execute(query, args)
            await db.commit()

    async def fetchone(self, query: str, *args):
        async with connect(self.path) as db:
            db.row_factory = Row
            async with db.execute(query, args) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetchall(self, query: str, *args):
        async with connect(self.path) as db:
            async with db.execute(query, args) as cursor:
                return await cursor.fetchall()

    async def start(self):
        pass

    async def close(self):
        pass

    async def get_or_create_user(self, id: int, php: str, name: str = "") -> User:
        user = await self.fetchone(self.q.get_user, id)
        if user:
            user["items"] = json.loads(user["items"])
            user["extra_emojis"] = json.loads(user["extra_emojis"])
            user["selected_emojis"] = json.loads(user["selected_emojis"])
            return User.model_validate(user)
        # Convert STD_EMOJIS to strings when creating new user
        std_emojis_str = [str(emoji) for emoji in Config.STD_EMOJIS[0:10]]
        await self.do(self.q.insert_user, id, Config.STD_ELO, Config.DEFAULT_CREDIT, Config.DEFAULT_GOLD, php or ",", json.dumps(std_emojis_str), name)
        return await self.get_or_create_user(id, php, name) 

    async def get_user(self, id:int) -> User:
        user = await self.fetchone(self.q.get_user, id)
        if user:
            user["items"] = json.loads(user["items"])
            user["extra_emojis"] = json.loads(user["extra_emojis"])
            user["selected_emojis"] = json.loads(user["selected_emojis"])
            return User.model_validate(user)
        raise ValueError("user is not exist")

    async def add_money(self, id: int, money: int | float):
        return await self.do(self.q.add_money, money, id)

    async def get_money(self, id: int):
        if id < 120 and Config.TEST_MODE:
            return 5000000
        try:
            return (await self.fetchone(
                self.q.get_money,
                id
            )).get("money") #type:ignore
        except AttributeError:
            return None

singleton = Database()
get_db = lambda: singleton