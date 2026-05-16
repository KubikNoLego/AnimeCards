import sys
import os
from loguru import logger

from aiogram import Dispatcher

from app.handlers import setup_routers as setup_handlers_routers
from app.middlewares import DBSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware

def setup_logger() -> None:
    """
    Настройка логирования с использованием loguru.
    """
    os.makedirs("logs", exist_ok=True)

    logger.remove()

    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    logger.add(
        "logs/bot.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        rotation="10 MB",
        retention="7 days"
    )

    logger.info("Логирование настроено успешно!")

def setup_routers(dp: Dispatcher):
    """Подключает все роутеры к диспетчеру."""
    setup_handlers_routers(dp)

def setup_middlewares(dp: Dispatcher, session_factory):
    """Настраивает middleware для диспетчера."""
    dp.message.middleware(
        DBSessionMiddleware(session_factory)
    )
    dp.callback_query.middleware(
        DBSessionMiddleware(session_factory)
    )
    dp.message.middleware(
        ThrottlingMiddleware(1.2)
    )

def setup_dispatcher(dp: Dispatcher, session_factory):
    """Настраивает диспетчер: middleware, роутеры."""
    setup_middlewares(dp, session_factory)
    setup_routers(dp)
    return dp