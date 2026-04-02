import sys

from aiogram import Dispatcher
from loguru import logger

from app.handlers import setup_routers as setup_handlers_routers
from app.middlewares import DBSessionMiddleware


def setup_logger():
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO", colorize=False, diagnose=True
    )
    logger.add("logs/bot.log", rotation="10 MB", encoding="utf-8",
            compression="zip", retention="3 days", serialize=True,
            enqueue=True
            )

    logger.success("Логирование настроено успешно!")



def setup_routers(dp: Dispatcher):
    """Подключает все роутеры к диспетчеру."""
    setup_handlers_routers(dp)

def setup_middlewares(dp: Dispatcher, session_factory):

    dp.message.middleware(
        DBSessionMiddleware(session_factory)
    )
    dp.callback_query.middleware(
        DBSessionMiddleware(session_factory)
    )


def setup_dispatcher(dp: Dispatcher, session_factory):

    setup_middlewares(dp, session_factory)
    setup_routers(dp)

    return dp