from .db import get_db
from .config import Config
import logging
import uvicorn
from .app import api, bot, dp
import asyncio

async def serverctl():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True
    )
    logger = logging.getLogger(__name__)
    await get_db().start()
    logger.info("Database started successfully")

    server = uvicorn.Server(
        config=uvicorn.Config(api, host=Config.HOST, port=Config.PORT, log_level="info")
    )
    
    while True:
        try:
            logger.info("Starting HTTP server and bot polling")
            await asyncio.gather(
                server.serve(),
                dp.start_polling(bot)
            )
            break  # если вышли нормально — выходим
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down...")
            break
        except Exception as e:
            logger.exception("Server crashed. Restarting in 5s...")
            await asyncio.sleep(5)

    await server.shutdown()
    await get_db().close()
    logger.info("Server control module stopped")