import asyncio
from datetime import timedelta, timedelta

from aiogram import Bot,Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import (create_async_engine,
                                    async_sessionmaker
                                    )
from loguru import logger

from config import config
from .loader import setup_logger, setup_dispatcher
from .bot import create_bot, create_dispatcher
from db import Base
from app.func.daily_updates import (
    _cleanup_expired_vip_subscriptions,
    _daily_coordinator
)

setup_logger()
bot = create_bot(config)
dp = create_dispatcher(config)


engine = create_async_engine(
    config.DB_URL.get_secret_value(),
    pool_size=20,
    max_overflow=30,
    pool_timeout=60.0,
    pool_recycle=3600,
    pool_pre_ping=True
)
_sessionmaker = async_sessionmaker(engine,expire_on_commit=False)

# Глобальные переменные для хранения ссылок на фоновые задачи
_daily_coordinator_task = None
_vip_cleanup_task = None

setup_dispatcher(dp,_sessionmaker)

@dp.startup()
async def on_startup():
    await bot.delete_webhook(True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Запуск ежедневных обновлений в фоновом режиме
    global _daily_coordinator_task, _vip_cleanup_task
    _daily_coordinator_task = asyncio.create_task(_daily_coordinator(_sessionmaker))
    _vip_cleanup_task = asyncio.create_task(_cleanup_expired_vip_subscriptions(_sessionmaker))
    logger.success("Бот успешно запущен")
    
@dp.shutdown()
async def on_shudown():
    # Отменяем фоновые задачи при завершении работы
    if _daily_coordinator_task and not _daily_coordinator_task.done():
        _daily_coordinator_task.cancel()
        try:
            await _daily_coordinator_task
        except asyncio.CancelledError:
            pass

    if _vip_cleanup_task and not _vip_cleanup_task.done():
        _vip_cleanup_task.cancel()
        try:
            await _vip_cleanup_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()
    logger.error("Бот отключён")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
