import sys

from loguru import logger

def setup_logger():
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function} | {message}",
        level="INFO", colorize=False
    )
    logger.add("logs/bot.log", rotation="10 MB", encoding="utf-8",
            compression="zip", retention="3 days", serialize=True
            )

    logger.success("Логирование настроено успешно!")