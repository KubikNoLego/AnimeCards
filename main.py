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
from db.requests import get_random_verse, get_daily_shop_items


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

            # Проверяем, существует ли текущая вселенная в Redis
            verse_data_json = await session.get("daily_verse")

            if verse_data_json:
                # Вселенная существует и актуальна (TTL еще не истек)
                logger.info("Ежедневная вселенная уже актуальна")
            else:
                # Выбираем новую вселенную
                async with _sessionmaker() as db_session:
                    new_verse: Verse = await get_random_verse(db_session)

                    if new_verse:
                        # Сохраняем только ID вселенной в Redis с TTL 24 часа
                        await session.set("daily_verse", str(new_verse.id), ex=24*60*60)
                        logger.info(f"Ежедневная вселенная обновлена. ID: {new_verse.id}")
                    else:
                        logger.warning("Не удалось получить новую вселенную для ежедневного обновления")

            await session.aclose()
        except Exception as e:
            logger.error(f"Ошибка в _daily_updates: {str(e)}", exc_info=True)
        await asyncio.sleep(600)  # Уменьшаем задержку до 10 минут для более быстрого обновления

async def _daily_shop_updates():
    while True:
        try:
            logger.info("Запуск проверки ежедневных обновлений магазина")
            session = Redis()

            # Проверяем, существуют ли текущие товары магазина в Redis
            shop_items = await session.get("shop_items")

            if shop_items:
                # Товары существуют и актуальны (TTL еще не истек)
                logger.info("Товары ежедневного магазина уже актуальны")
            else:
                # Генерируем новые товары для магазина
                async with _sessionmaker() as db_session:
                    daily_items = await get_daily_shop_items(db_session)

                    if daily_items and len(daily_items) > 0:
                        # Сохраняем только ID карточек для ежедневного магазина с TTL 24 часа
                        shop_items_ids = [str(card.id) for card in daily_items]
                        await session.set("shop_items", ",".join(shop_items_ids), ex=24*60*60)
                        logger.info(f"Ежедневный магазин обновлен. Товары: {len(daily_items)} шт.")
                    else:
                        logger.warning("Не удалось получить товары для ежедневного магазина")

            await session.aclose()
        except Exception as e:
            logger.error(f"Ошибка в _daily_shop_updates: {str(e)}", exc_info=True)
        await asyncio.sleep(600)  # Уменьшаем задержку до 10 минут для более быстрого обновления

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
    asyncio.create_task(_daily_shop_updates())
    logger.info("Бот успешно запущен")
@dp.shutdown()
async def on_shudown():
    await _engine.dispose()
    logger.warning("Бот отключён")
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
