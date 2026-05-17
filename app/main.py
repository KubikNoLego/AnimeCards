import asyncio

from loguru import logger

from app.config import config

from app.database.requests import RedisRequests, get_redis
from app.loader import setup_logger, setup_dispatcher
from app.bot import create_bot, create_dispatcher
from app.database import Base, create_sessionmaker, create_engine
from app.services.schedule import SchedulerManager


def main() -> None:
    """Точка входа приложения."""
    
    # Настройка логирования с учетом debug режима
    setup_logger()
    
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
        
        scheduler.set_stats_target(chat_id=config.CHAT_ID,
                                message_id=config.MESSAGE_ID)
        redis = get_redis()
        redis = RedisRequests(redis)
        if not await redis.daily_verse():
            await scheduler._run_update_verse()
        scheduler.start()
        
        logger.success("Бот успешно запущен")
    
    @dp.shutdown()
    async def on_shutdown():
        scheduler.shutdown()
        
        await engine.dispose()
        logger.info("Бот отключён")
    
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()