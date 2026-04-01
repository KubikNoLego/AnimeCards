import asyncio
from datetime import datetime
import os

from aiogram import Bot
from sqlalchemy.ext.asyncio import (
                                    AsyncSession,
                                    async_sessionmaker
                                    )
from sqlalchemy import delete, select
from loguru import logger

from db import Verse, DB, VipSubscription, User, Clan, Card, Trade, Profile, ClanMember, Promo, UserCards, PromoUsers
from app.func import MSK_TIMEZONE
from sqlalchemy import func, distinct, and_

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
async def _update_users_info(bot: Bot, db_session: AsyncSession) -> bool:
    """Обновляет имена и username пользователей из Telegram."""
    users = await db_session.scalars(select(User))
    users_list = users.all()
    
    updated_count = 0
    failed_count = 0
    
    for user in users_list:
        try:
            # Получаем актуальную информацию о пользователе из Telegram
            chat_member = await bot.get_chat(user.id)
            
            # Обновляем username и name только если они изменились
            new_username = chat_member.username
            new_name = chat_member.full_name
            
            if user.username != new_username or user.name != new_name:
                user.username = new_username
                user.name = new_name
                updated_count += 1
        except Exception as e:
            # Проверяем, не заблокировал ли пользователь бота
            if "Forbidden" in str(e) or "blocked" in str(e).lower():
                failed_count += 1
                logger.warning(f"Пользователь {user.id} заблокировал бота")
            else:
                failed_count += 1
                logger.error(f"Ошибка при обновлении пользователя {user.id}: {e}")
    
    if updated_count > 0:
        await db_session.commit()
        logger.info(f"Обновлено {updated_count} пользователей, {failed_count} ошибок")
    
    return updated_count > 0

@logger.catch
async def _daily_coordinator(bot: Bot, sessionmaker: async_sessionmaker):
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
                    users_updated = await _update_users_info(bot, db_session)
                    await _create_backup()

                if current_date.weekday() == 0:
                    await _rebalance_clans(db_session)

                # Обновляем дату последнего обновления только если хотя бы одна задача выполнилась успешно
                if verse_updated or shop_updated or vip_updated or users_updated:
                    await session.set("last_update",
                        current_date.strftime("%Y-%m-%d"), ex=24*60*60)

            await session.aclose()
        except Exception as e:
            logger.exception(f"Ошибка в _daily_coordinator")
            await asyncio.sleep(60)

        await asyncio.sleep(3600)


@logger.catch
async def _create_backup():
    """Создаёт бэкап базы данных PostgreSQL."""
    import subprocess
    from configR import config

    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    db_url = config.DB_URL.get_secret_value()
    db_url_parsed = db_url.replace("postgresql+asyncpg://", "postgresql://")

    timestamp = datetime.now(MSK_TIMEZONE).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")

    try:
        # Получаем параметры подключения
        from urllib.parse import urlparse
        parsed = urlparse(db_url_parsed)

        env = os.environ.copy()
        env["PGPASSWORD"] = parsed.password

        cmd = [
            "pg_dump",
            "-h", parsed.hostname or "localhost",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "postgres",
            "-d", parsed.path.lstrip("/"),
            "-f", backup_file
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Бэкап базы данных создан: {backup_file}")

            # Удаляем старые бэкапы (оставляем последние 7)
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith(".sql")])
            while len(backups) > 7:
                old_backup = backups.pop(0)
                os.remove(os.path.join(backup_dir, old_backup))
                logger.info(f"Удалён старый бэкап: {old_backup}")

            return True
        else:
            logger.error(f"Ошибка при создании бэкапа: {stderr.decode()}")
            return False

    except FileNotFoundError:
        logger.error("pg_dump не найден. Убедитесь, что PostgreSQL установлен.")
        return False
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при создании бэкапа: {e}")
        return False

async def _get_stats_text(db_session) -> str:
    """Генерирует текст со статистикой бота."""
    try:
        # Основные счётчики
        total_players = (await db_session.execute(select(func.count(User.id)))).scalar()
        total_cards = (await db_session.execute(select(func.count(Card.id)))).scalar()
        total_clans = (await db_session.execute(select(func.count(Clan.id)))).scalar()
        
        # Рефералы
        total_referrals = (await db_session.execute(select(func.count()))).scalar()
        
        # VIP пользователи
        current_time = datetime.now(MSK_TIMEZONE)
        vip_count = (await db_session.execute(
            select(func.count(VipSubscription.user_id))
            .where(VipSubscription.end_date > current_time)
        )).scalar()
        
        # Активные пользователи (открывали карты за последние 24 часа)
        from datetime import timedelta
        day_ago = current_time - timedelta(hours=24)
        active_users = (await db_session.execute(
            select(func.count(User.id))
            .where(User.last_open >= day_ago)
        )).scalar()
        
        # Общее количество карт у всех пользователей (открытые карты)
        total_opened = (await db_session.execute(
            select(func.count()).select_from(UserCards)
        )).scalar()
        
        # Количество активаций всех промокодов
        total_promo_activations = (await db_session.execute(
            select(func.count(PromoUsers.user_id))
        )).scalar()
        
        # Формируем текст статистики
        stats_text = (
            "<i>📊 Статистика бота</i>\n\n"
            "<b>👥 Пользователи:</b>\n"
            f"  • Всего игроков: <b>{total_players or 0}</b>\n"
            f"  • Активных за 24ч: <b>{active_users or 0}</b>\n\n"
            
            "<b>🃏 Карты:</b>\n"
            f"  • Всего карт доступно: <b>{total_cards or 0}</b>\n"
            f"  • Открыто карт игроками: <b>{total_opened or 0}</b>\n\n"
            
            "<b>🤝 Активность:</b>\n"
            f"  • Рефералов: <b>{total_referrals or 0}</b>\n\n"
            
            "<b>🏰 Кланы:</b>\n"
            f"  • Всего кланов: <b>{total_clans or 0}</b>\n\n"
            
            "<b>⭐ VIP:</b>\n"
            f"  • VIP подписчиков: <b>{vip_count or 0}</b>\n\n"
            
            "<b>🎁 Промокоды:</b>\n"
            f"  • Активаций промокодов: <b>{total_promo_activations or 0}</b>\n\n"
        )
        
        return stats_text
        
    except Exception as e:
        logger.exception(f"Ошибка при получении статистики: {e}")
        return "<i>📊 Статистика бота</i>\n\n<i>Ошибка при загрузке данных...</i>"


async def _edit_stats(bot: Bot, chat_id: int | str, message_id: int, db_sessionmaker, interval: int = 600):
    while True:
        try:
            # Получаем актуальный текст статистики
            async with db_sessionmaker() as db_session:
                display_text = await _get_stats_text(db_session)
            
            await bot.edit_message_text(
                text=display_text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="HTML"
            )
        except Exception as e:
            # Игнорируем ошибки, если сообщение не изменилось
            if "message is not modified" not in str(e).lower():
                # Проверяем, не было ли удалено сообщение
                if "message to edit not found" in str(e).lower() or "message can't be edited" in str(e).lower():
                    logger.warning(f"Сообщение {message_id} в чате {chat_id} больше недоступно для редактирования")
                    break
                logger.exception(f"Ошибка обновления статистики в чате {chat_id}, сообщение {message_id}: {e}")
        
        await asyncio.sleep(interval)
