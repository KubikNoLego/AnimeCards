import asyncio
from datetime import timedelta

from aiogram import Bot,Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import (create_async_engine,
                                    async_sessionmaker
                                    )
from loguru import logger

from configR import config
from app.handlers import setup_routers
from app.middlewares import DBSessionMiddleware
from db import Base
from app.func import setup_logger
from app.func.daily_updates import (
    _daily_coordinator
)

setup_logger()

bot = Bot(
    config.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
dp = Dispatcher(storage=RedisStorage.from_url(
    config.REDIS_URL.get_secret_value(), 
    state_ttl=timedelta(days=3),
    data_ttl=timedelta(days=1))
    )


engine = create_async_engine(
    config.DB_URL.get_secret_value(),
    pool_size=20,
    max_overflow=30,
    pool_timeout=60.0,
    pool_recycle=3600,
    pool_pre_ping=True
)
_sessionmaker = async_sessionmaker(engine,expire_on_commit=False)

# Глобальная переменная для хранения ссылки на фоновую задачу
_daily_coordinator_task = None

dp.message.middleware(DBSessionMiddleware(_sessionmaker))
dp.callback_query.middleware(DBSessionMiddleware(_sessionmaker))
dp.include_router(router=setup_routers())

@dp.startup()
async def on_startup():
    await bot.delete_webhook(True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Запуск ежедневных обновлений в фоновом режиме
    global _daily_coordinator_task
    _daily_coordinator_task = asyncio.create_task(_daily_coordinator(bot, _sessionmaker))
    logger.success("Бот успешно запущен")
    
@dp.shutdown()
async def on_shutdown():
    # Отменяем фоновые задачи при завершении работы
    if _daily_coordinator_task and not _daily_coordinator_task.done():
        _daily_coordinator_task.cancel()
        try:
            await _daily_coordinator_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()
    logger.info("Бот отключён")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
