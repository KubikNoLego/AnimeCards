import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import (
                                    AsyncSession,
                                    async_sessionmaker
                                    )
from sqlalchemy import delete, select
from loguru import logger

from db import Verse,DB,VipSubscription,User,Clan
from app.func import MSK_TIMEZONE


@logger.catch
async def _cleanup_expired_vip_subscriptions(sessionmaker:async_sessionmaker):
    """Фоновая задача для очистки истекших VIP подписок."""
    while True:
        try:
            current_time = datetime.now(MSK_TIMEZONE)

            async with sessionmaker() as session:
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
                    logger.info(
                        f"Удалено {expired_count} истекших VIP подписок"
                        )

        except Exception as e:
            logger.exception(
                f"Ошибка при очистке истекших VIP подписок")
            await asyncio.sleep(60)

        await asyncio.sleep(3600)

@logger.catch
async def _update_daily_verse(session, db_session):
    """Обновляем ежедневную вселенную."""
    new_verse: Verse = await DB(db_session).get_random_verse()
    if new_verse:
        await session.set("daily_verse", str(new_verse.id), ex=24*60*60)
        logger.info(
f"Ежедневная вселенная обновлена. ID: {new_verse.id}")
        return True
    else:
        logger.error(
        "Не удалось получить новую вселенную для ежедневного обновления")
        return False

@logger.catch
async def _update_daily_shop(session, db_session):
    """Обновляем ежедневный магазин."""
    daily_items = await DB(db_session).get_daily_shop_items()
    if daily_items and len(daily_items) > 0:
        shop_items_ids = [str(card.id) for card in daily_items]
        await session.set("shop_items", ",".join(shop_items_ids), ex=24*60*60)
        logger.info(
f"Ежедневный магазин обновлен. Товары: {len(daily_items)} шт.")
        return True
    else:
        logger.error("Не удалось получить товары для ежедневного магазина")
        return False

@logger.catch
async def _add_vip_free_opens(db_session):
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
        logger.info(
            f"Добавлено бесплатное открытие {updated_count} VIP пользователям")
    return updated_count > 0

@logger.catch
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

@logger.catch
async def _daily_coordinator(sessionmaker:async_sessionmaker):
    """Главная координирующая функция для всех ежедневных задач."""
    from redis.asyncio import Redis
    while True:
        try:
            current_date = datetime.now(MSK_TIMEZONE).date()
            session = Redis()

            last_update_date_str = await session.get("last_update")

            if last_update_date_str:
                last_update_date_str = last_update_date_str.decode('utf-8')
                last_update_date = datetime.strptime(last_update_date_str,
                                                    "%Y-%m-%d").date()
            else:
                last_update_date = None

            # Если сегодня еще не обновляли, выполняем все ежедневные задачи
            if not last_update_date or last_update_date < current_date:
                async with sessionmaker() as db_session:
                    verse_updated = await _update_daily_verse(session, db_session)
                    shop_updated = await _update_daily_shop(session, db_session)
                    vip_updated = await _add_vip_free_opens(db_session)

                if current_date.weekday() == 0:
                    await _rebalance_clans(db_session)

                # Обновляем дату последнего обновления только если хотя бы одна задача выполнилась успешно
                if verse_updated or shop_updated or vip_updated:
                    await session.set("last_update",
                        current_date.strftime("%Y-%m-%d"), ex=24*60*60)

            await session.aclose()
        except Exception as e:
            logger.exception(f"Ошибка в _daily_coordinator")
            await asyncio.sleep(60)

        await asyncio.sleep(3600)
