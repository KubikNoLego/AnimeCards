
import asyncio
from datetime import timedelta,datetime, timezone, timedelta

from db.models import Clan

# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

from aiogram import Bot,Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,async_sessionmaker
from sqlalchemy import delete, select
from loguru import logger

from configR import config
from app.handlers import setup_routers
from app.middlewares import DBSessionMiddleware
from db import Base,Verse,DB,RedisRequests,VipSubscription,User


# Настройка логирования: записывать в файл `log.txt`, ротация при 10 МБ
logger.remove()
logger.add("log.txt", rotation="10 MB", encoding="utf-8", level="INFO")

bot = Bot(config.BOT_TOKEN.get_secret_value(),default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage.from_url(config.REDIS_URL.get_secret_value(), state_ttl=timedelta(days=7)))


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



async def _cleanup_expired_vip_subscriptions():
    """Фоновая задача для очистки истекших VIP подписок."""
    while True:
        try:
            current_time = datetime.now(MSK_TIMEZONE)

            async with _sessionmaker() as session:
                # Получаем все активные VIP подписки
                result = await session.execute(select(VipSubscription))
                vip_subscriptions = result.scalars().all()

                expired_count = 0

                for subscription in vip_subscriptions:
                    if subscription.end_date <= current_time:
                        # Подписка истекла, удаляем ее
                        await session.execute(
                            delete(VipSubscription)
                            .where(VipSubscription.id == subscription.id)
                        )
                        expired_count += 1

                if expired_count > 0:
                    await session.commit()
                    logger.info(f"Удалено {expired_count} истекших VIP подписок")

        except Exception as e:
            logger.error(f"Ошибка при очистке истекших VIP подписок: {str(e)}", exc_info=True)
            await asyncio.sleep(60)

        await asyncio.sleep(3600)

async def _update_daily_verse(session, db_session, current_date):
    """Обновляем ежедневную вселенную."""
    new_verse: Verse = await DB(db_session).get_random_verse()
    if new_verse:
        await session.set("daily_verse", str(new_verse.id), ex=24*60*60)
        logger.info(f"Ежедневная вселенная обновлена. ID: {new_verse.id}, Дата: {current_date}")
        return True
    else:
        logger.warning("Не удалось получить новую вселенную для ежедневного обновления")
        return False

async def _update_daily_shop(session, db_session, current_date):
    """Обновляем ежедневный магазин."""
    daily_items = await DB(db_session).get_daily_shop_items()
    if daily_items and len(daily_items) > 0:
        shop_items_ids = [str(card.id) for card in daily_items]
        await session.set("shop_items", ",".join(shop_items_ids), ex=24*60*60)
        logger.info(f"Ежедневный магазин обновлен. Товары: {len(daily_items)} шт., Дата: {current_date}")
        return True
    else:
        logger.warning("Не удалось получить товары для ежедневного магазина")
        return False

async def _add_vip_free_opens(db_session, current_date):
    """Добавляем бесплатные открытия VIP пользователям."""
    current_time = datetime.now(MSK_TIMEZONE)
    result = await db_session.execute(
        select(User)
        .join(User.vip)
        .where(VipSubscription.end_date > current_time)
    )
    vip_users = result.scalars().all()

    updated_count = 0
    for user in vip_users:
        user.free_open += 1
        updated_count += 1

    if updated_count > 0:
        await db_session.commit()
        logger.info(f"Добавлено бесплатное открытие {updated_count} VIP пользователям")
    return updated_count > 0

async def _rebalance_clans(db_session: AsyncSession):
    clans = await db_session.scalars(select(Clan))
    clans_result = clans.all()
    for clan in clans_result:
        
        added_sum = clan.balance // len(clan.members)
        
        users = clan.members
        for user in users:
            user.contribution = 0
            user = user.user
            user.balance += added_sum
        clan.balance = 0
    
    await db_session.commit()


async def _daily_coordinator():
    """Главная координирующая функция для всех ежедневных задач."""
    while True:
        try:
            current_date = datetime.now(MSK_TIMEZONE).date()
            session = Redis()

            last_update_date_str = await session.get("last_update")

            if last_update_date_str:
                last_update_date_str = last_update_date_str.decode('utf-8')
                last_update_date = datetime.strptime(last_update_date_str, "%Y-%m-%d").date()
            else:
                last_update_date = None

            # Если сегодня еще не обновляли, выполняем все ежедневные задачи
            if not last_update_date or last_update_date < current_date:
                async with _sessionmaker() as db_session:
                    verse_updated = await _update_daily_verse(session, db_session, current_date)
                    shop_updated = await _update_daily_shop(session, db_session, current_date)
                    vip_updated = await _add_vip_free_opens(db_session, current_date)

                    if current_date.weekday() == 0:
                        await _rebalance_clans(db_session)


                    # Обновляем дату последнего обновления только если хотя бы одна задача выполнилась успешно
                    if verse_updated or shop_updated or vip_updated:
                        await session.set("last_update", current_date.strftime("%Y-%m-%d"), ex=24*60*60)
                        logger.info(f"Все ежедневные задачи выполнены. Дата: {current_date}")

            await session.aclose()
        except Exception as e:
            logger.error(f"Ошибка в _daily_coordinator: {str(e)}", exc_info=True)
            await asyncio.sleep(60)

        await asyncio.sleep(3600)  # Проверяем каждые 60 минут

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
    _daily_coordinator_task = asyncio.create_task(_daily_coordinator())
    _vip_cleanup_task = asyncio.create_task(_cleanup_expired_vip_subscriptions())
    logger.info("Бот успешно запущен")
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
    logger.warning("Бот отключён")
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))