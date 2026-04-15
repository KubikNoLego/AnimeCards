import argparse
import asyncio
import sys

from loguru import logger
from aiogram.types import Update

# Импортируем config из app.config
from app.config import config

# Импортируем из app
from app.database.requests import RedisRequests, get_redis
from app.loader import setup_logger, setup_dispatcher
from app.bot import create_bot, create_dispatcher
from app.database import Base, create_sessionmaker, create_engine
from app.services.schedule import SchedulerManager


def parse_args() -> argparse.Namespace:
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Telegram бот для управления карточками аниме",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m app.main              # Запуск в обычном режиме
  python -m app.main --debug      # Запуск в режиме отладки
  python -m app.main -d           # Короткая форма для debug режима
        """
    )
    
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Запуск в режиме отладки (подробные логи, отключены фоновые задачи)"
    )
    
    return parser.parse_args()


def main() -> None:
    """Точка входа приложения."""
    args = parse_args()
    
    # Настройка логирования с учетом debug режима
    setup_logger(debug=args.debug)
    
    if args.debug:
        logger.info("Запуск в режиме отладки (debug mode)")
        logger.warning("Фоновые задачи (ежедневные обновления, статистика) отключены")
    
    bot = create_bot(config)
    dp = create_dispatcher(config)
    
    engine = create_engine(config)
    sessionmaker = create_sessionmaker(engine)

    scheduler = SchedulerManager(bot, sessionmaker)

    setup_dispatcher(dp, sessionmaker)
    
    @dp.startup()
    async def on_startup():
        await bot.delete_webhook(drop_pending_updates=True)
        
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        
        # Запуск фоновых задач только в обычном режиме (не debug)
        if not args.debug:
            scheduler.set_stats_target(chat_id=config.CHAT_ID,
                                    message_id=config.MESSAGE_ID)
            redis = get_redis()
            redis = RedisRequests(redis)
            if not await redis.daily_verse():
                await scheduler._run_update_verse()            
            scheduler.start()
        else:
            logger.info("Фоновые задачи пропущены (debug режим)")
        
        logger.success("Бот успешно запущен")
    
    @dp.shutdown()
    async def on_shutdown():

        if not args.debug:
            await scheduler.shutdown()
        
        await engine.dispose()
        logger.info("Бот отключён")
    
    # Запуск поллинга
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()