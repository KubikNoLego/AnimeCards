import sys

from loguru import logger

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