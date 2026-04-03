import sys
import logging
from typing import Optional

from aiogram import Dispatcher
from loguru import logger

from app.handlers import setup_routers as setup_handlers_routers
from app.middlewares import DBSessionMiddleware


class InterceptHandler(logging.Handler):
    """Handler that intercepts standard logging and redirects to loguru."""
    
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(debug: bool = False) -> None:
    """
    Настройка логирования с поддержкой debug режима.
    
    Args:
        debug: Если True, устанавливает уровень DEBUG и включает детальную отладку
    """
    logger.remove()
    
    # Формат для обычного режима
    format_info = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # Формат для debug режима (более детальный)
    format_debug = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<magenta>thread:{thread.id}</magenta> | "
        "<level>{message}</level>"
    )
    
    # Выбираем формат и уровень в зависимости от режима
    log_format = format_debug if debug else format_info
    log_level = "DEBUG" if debug else "INFO"
    
    # Добавляем вывод в консоль
    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,  # Включаем цвета
        diagnose=debug,  # Подробная отладка только в debug режиме
        backtrace=debug,  # Трассировка только в debug режиме
    )
    
    # Добавляем вывод в файл (всегда, но с разным уровнем)
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        encoding="utf-8",
        compression="zip",
        retention="7 days" if debug else "3 days",
        level=log_level,
        serialize=False,  # Отключаем JSON для удобства чтения
        enqueue=True,
        format=log_format,
    )
    
    # Перехватываем стандартный logging (для библиотек типа aiogram, sqlalchemy)
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
    
    # Настраиваем уровень для конкретных библиотек
    if debug:
        # В debug режиме показываем больше логов от библиотек
        logging.getLogger("aiogram").setLevel(logging.DEBUG)
        logging.getLogger("sqlalchemy").setLevel(logging.INFO)
    else:
        # В обычном режиме скрываем шумные библиотеки
        logging.getLogger("aiogram").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    logger.success("Логирование настроено успешно!" + (" (DEBUG режим)" if debug else ""))


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


def setup_dispatcher(dp: Dispatcher, session_factory):
    """Настраивает диспетчер: middleware, роутеры."""
    setup_middlewares(dp, session_factory)
    setup_routers(dp)
    return dp