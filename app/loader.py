import sys
import os
import logging

from loguru import logger
from aiogram import Dispatcher

from app.handlers import setup_routers as setup_handlers_routers
from app.middlewares import DBSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.middlewares.userupdate import UpdateUserMiddleware

class InterceptHandler(logging.Handler):
    """
    Перенаправляет стандартный logging в Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2

        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(
            depth=depth,
            exception=record.exc_info
        ).log(level, record.getMessage())


def setup_logger() -> None:
    """
    Настройка Loguru и перехват логов стандартного logging.
    """

    os.makedirs("logs", exist_ok=True)

    logger.remove()

    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    logger.add(
        "logs/bot.log",
        level="TRACE",
        encoding="utf-8",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{process.name}:{thread.name} | "
            "{name}:{function}:{line} - "
            "{message}"
        ),
    )

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.NOTSET)

    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    logger.info("Логирование настроено")

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
    dp.message.middleware(
        UpdateUserMiddleware(session_factory)
    )

def setup_dispatcher(dp: Dispatcher, session_factory):
    """Настраивает диспетчер: middleware, роутеры."""
    setup_middlewares(dp, session_factory)
    setup_routers(dp)
    return dp