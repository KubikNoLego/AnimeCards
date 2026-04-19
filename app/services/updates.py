import asyncio
from datetime import datetime
import os

from aiogram import Bot
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card, Clan, PromoUsers, User, UserCards, VipSubscription
from app.database.requests import DB, RedisRequests
from app.utils.consts import MSK_TIMEZONE


@logger.catch
async def update_verse(session: AsyncSession) -> bool:
    """Обновляет ежедневную вселенную в Redis."""
    db = DB(session)
    new_verse = await db.card.get_random_verse()
    if new_verse:
        await RedisRequests.set_verse(new_verse.id)
        logger.info(f"Ежедневная вселенная обновлена. ID: {new_verse.id}")
        return True
    else:
        logger.error(
            "Не удалось получить новую вселенную для ежедневного обновления")
        return False

@logger.catch
async def add_free_opens(session: AsyncSession) -> bool:
    now = datetime.now(MSK_TIMEZONE)
    result = await session.execute(
        select(User)
        .join(User.vip)
        .where(VipSubscription.end_date > now)
    )
    vip_users = result.scalars().all()

    updated_count = 0
    for user in vip_users:
        user.free_open += 1
        updated_count += 1

    if updated_count > 0:
        await session.commit()
        logger.info(
            f"Добавлено бесплатное открытие {updated_count} VIP пользователям")
    return updated_count > 0

@logger.catch
async def clan_rebalance(session: AsyncSession) -> None:
    clans = await session.scalars(select(Clan))
    clans_result = clans.all()
    for clan in clans_result:

        added_sum = clan.balance // len(clan.members)

        users = clan.members
        for user in users:
            user.contribution = 0
            user = user.user
            user.balance += added_sum
        clan.balance = 0

    await session.commit()

@logger.catch
async def update_info_users(bot: Bot, session: AsyncSession) -> bool:
    users = await session.scalars(select(User))
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
        await session.commit()
        logger.info(f"Обновлено {updated_count} пользователей, {failed_count} ошибок")
    
    return updated_count > 0


@logger.catch
async def _create_backup() -> bool:
    """Создаёт бэкап базы данных PostgreSQL."""
    import subprocess
    from app.config import config

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
        _, stderr = await process.communicate()

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
    
@logger.catch
async def get_stats(session: AsyncSession) -> str:
    try:
        # Основные счётчики
        total_players = (await session.execute(select(func.count(User.id)))).scalar()
        total_cards = (await session.execute(select(func.count(Card.id)))).scalar()
        total_clans = (await session.execute(select(func.count(Clan.id)))).scalar()
        
        # Рефералы
        total_referrals = (await session.execute(select(func.count()))).scalar()
        
        # VIP пользователи
        current_time = datetime.now(MSK_TIMEZONE)
        vip_count = (await session.execute(
            select(func.count(VipSubscription.user_id))
            .where(VipSubscription.end_date > current_time)
        )).scalar()
        
        # Активные пользователи (открывали карты за последние 24 часа)
        from datetime import timedelta
        day_ago = current_time - timedelta(hours=24)
        active_users = (await session.execute(
            select(func.count(User.id))
            .where(User.last_open >= day_ago)
        )).scalar()
        
        # Общее количество карт у всех пользователей (открытые карты)
        total_opened = (await session.execute(
            select(func.count()).select_from(UserCards)
        )).scalar()
        
        # Количество активаций всех промокодов
        total_promo_activations = (await session.execute(
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
    
@logger.catch
async def edit_stats(session: AsyncSession, bot: Bot, chat_id: int | str,
                    message_id: int):
    try:
        display_text = await get_stats(session)
        
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
                return
            logger.exception(f"Ошибка обновления статистики в чате {chat_id}, сообщение {message_id}: {e}")