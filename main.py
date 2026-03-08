import asyncio
from datetime import timedelta,datetime, timedelta

from aiogram import Bot,Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import (create_async_engine,
                                    AsyncSession,
                                    async_sessionmaker
                                    )
from sqlalchemy import delete, select
from loguru import logger
from redis.asyncio import Redis

from configR import config
from app.handlers import setup_routers
from app.middlewares import DBSessionMiddleware
from db import Base,Verse,DB,VipSubscription,User,Clan
from app.func import MSK_TIMEZONE, setup_logger
from app.func.daily_updates import (
    _cleanup_expired_vip_subscriptions,
    _update_daily_verse,
    _update_daily_shop,
    _add_vip_free_opens,
    _rebalance_clans,
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


_engine = create_async_engine(
    config.DB_URL.get_secret_value(),
    pool_size=20,
    max_overflow=30,
    pool_timeout=60.0,
    pool_recycle=3600,
    pool_pre_ping=True
)
_sessionmaker = async_sessionmaker(_engine,expire_on_commit=False)

# Глобальные переменные для хранения ссылок на фоновые задачи
_daily_coordinator_task = None
_vip_cleanup_task = None

dp.message.middleware(DBSessionMiddleware(_sessionmaker))
dp.callback_query.middleware(DBSessionMiddleware(_sessionmaker))
dp.include_router(router=setup_routers())

@dp.startup()
async def on_startup():
    await bot.delete_webhook(True)

    async with _engine.begin() as connection:
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

    await _engine.dispose()
    logger.error("Бот отключён")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
