import asyncio
from datetime import timedelta,datetime, timezone

from aiogram import Bot,Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage

from redis.asyncio import Redis

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,async_sessionmaker
from loguru import logger

from db import Base,Verse
from configR import config
from app.handlers import setup_routers
from app.middlewares import DBSessionMiddleware
from db.requests import get_random_verse


# Настройка логирования: записывать в файл `log.txt`, ротация при 10 МБ
logger.remove()
logger.add("log.txt", rotation="10 MB", encoding="utf-8", level="INFO")

bot = Bot(config.BOT_TOKEN.get_secret_value(),default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage.from_url(config.REDIS_URL.get_secret_value(), state_ttl=timedelta(days=7)))


_engine = create_async_engine(config.DB_URL.get_secret_value())
_sessionmaker = async_sessionmaker(_engine,expire_on_commit=False)
# Middleware проксирует сессию БД в обработчики сообщений и callback'и


async def _daily_updates():
    while True:
        try:
            logger.info("Запуск проверки ежедневных обновлений")
            session = Redis()
            current_date = datetime.now(timezone.utc).date()
            last_date_str = await session.get("last_update")
            if last_date_str:
                last_date = datetime.strptime(last_date_str.decode("utf-8"),"%Y-%m-%d").date()
            else:
                last_date = current_date - timedelta(days=1)

            if current_date > last_date:
                logger.info("Начало обновления ежедневной вселенной")
                async with _sessionmaker() as db_session:
                    new_verse: Verse = await get_random_verse(db_session)

                    if new_verse:
                        await session.set("verse",new_verse.id)
                        await session.set("last_update", current_date.isoformat())
                        logger.info(f"Ежедневная вселенная обновлена. ID: {new_verse.id}")
                    else:
                        logger.warning("Не удалось получить новую вселенную для ежедневного обновления")
            await session.aclose()
        except Exception as e:
            logger.error(f"Ошибка в _daily_updates: {str(e)}", exc_info=True)
        await asyncio.sleep(3600)

dp.message.middleware(DBSessionMiddleware(_sessionmaker))
dp.callback_query.middleware(DBSessionMiddleware(_sessionmaker))
dp.include_router(router=setup_routers())
@dp.startup()
async def on_startup():
    await bot.delete_webhook(True)

    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Запуск ежедневных обновлений в фоновом режиме
    asyncio.create_task(_daily_updates())
    logger.info("Бот успешно запущен")
@dp.shutdown()
async def on_shudown():
    await _engine.dispose()
    logger.warning("Бот отключён")
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
