import asyncio
from datetime import datetime,timedelta
import os

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card, Clan, PromoUsers, User, UserCards, VipSubscription
from app.database.requests import DB
from app.utils.constants import MSK_TIMEZONE



async def update_verse(session: AsyncSession) -> bool:
    """Обновляет ежедневную вселенную в Redis."""
    db = DB(session)
    new_verse = await db.verse.update_daily_verse()
    if new_verse:
        logger.info(f"Ежедневная вселенная обновлена. ID: {new_verse.id}")
        return True
    else:
        logger.error(
            "Не удалось получить новую вселенную для ежедневного обновления")
        return False


async def add_free_opens(session: AsyncSession) -> bool:

    stmt = (
        update(User)
        .where(
            User.id.in_(
                select(VipSubscription.user_id)
                .where(VipSubscription.end_date > func.now())
            )
        )
        .values(
            free_standard_opens=User.free_standard_opens + 1
        )
    )

    await session.execute(stmt)
    await session.commit()

async def remove_expired_vip_subscriptions(session: AsyncSession, bot: Bot = None) -> int:
    """
    Удаляет просроченные VIP подписки и сбрасывает VIP статус пользователей.
    Отправляет уведомления пользователям о завершении подписки.
    Удаляет VIP титул (ID 21) из разблокированных титулов пользователя.

    Args:
        session: Асинхронная сессия базы данных
        bot: Экземпляр бота для отправки уведомлений (опционально)

    Returns:
        Количество удаленных подписок
    """
    now = datetime.now(MSK_TIMEZONE)

    result = await session.execute(
        select(VipSubscription)
        .where(VipSubscription.end_date <= now)
    )
    expired_subscriptions = result.scalars().all()

    removed_count = 0
    notified_count = 0

    for subscription in expired_subscriptions:
        user = subscription.user

        if user:
            await session.delete(subscription)
            removed_count += 1

            if bot:
                try:
                    await bot.send_message(
                        chat_id=user.id,
                        text="💔 Ваша VIP подписка истекла\n\n"
                            "Вы больше не получаете ежедневные бесплатные открытия и другие VIP привилегии. "
                            "Чтобы снова стать VIP пользователем, приобретите новую подписку в магазине."
                    )
                    notified_count += 1
                    user.profile.title = 16

                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление пользователю {user.id} об истечении VIP: {e}")

            vip_title = None
            for title in user.titles:
                if title.title_id == 21:
                    vip_title = title
                    break

            if vip_title:
                user.profile.title_id = 16
                await session.delete(vip_title)
                logger.info(f"Удалён VIP титул (ID 21) у пользователя {user.id}")

    if removed_count > 0:
        await session.commit()
        logger.info(f"Удалено {removed_count} просроченных VIP подписок, отправлено {notified_count} уведомлений")

    return removed_count


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

async def create_backup() -> bool:
    """Создаёт бэкап базы данных PostgreSQL."""
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
    

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

async def edit_stats(bot: Bot, message_id: int, chat_id: int, 
                    session: AsyncSession):
    try:
        display_text = await get_stats(session)

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=display_text,
        )
        return True

    except TelegramForbiddenError:
        logger.warning("Бот больше не имеет доступа к чату.")
        return False

    except TelegramBadRequest as e:
        error = str(e).lower()

        if "message is not modified" in error:
            return True

        if (
            "message to edit not found" in error
            or "message can't be edited" in error
        ):
            logger.warning(
                f"Сообщение {message_id} больше недоступно."
            )
            return False

        logger.exception("Ошибка Telegram при обновлении статистики.")
        return False

    except Exception:
        logger.exception("Неожиданная ошибка при обновлении статистики.")
        return False