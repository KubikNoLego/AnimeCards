# schedule.py (полностью исправленная версия)

from datetime import datetime, time
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.requests import RedisRequests, get_redis
from app.services.updates import (
    update_info_users, update_verse, add_free_opens,
    clan_rebalance, create_backup, edit_stats
)
from app.utils.constants import MSK_TIMEZONE


class SchedulerManager:
    """Менеджер планировщика для выполнения фоновых задач."""

    def __init__(self, bot, sessionmaker):
        self.bot = bot
        self.sessionmaker = sessionmaker
        self.scheduler = AsyncIOScheduler(timezone=MSK_TIMEZONE)
        self.stats_chat_id = None
        self.stats_message_id = None

    def set_stats_target(self, chat_id: int | str, message_id: int) -> None:
        """Устанавливает целевой чат и сообщение для обновления статистики."""
        self.stats_chat_id = chat_id
        self.stats_message_id = message_id

    async def _update_info_users(self):
        async with self.sessionmaker() as session:
            await update_info_users(self.bot, session)

    async def _run_update_verse(self):
        """Выполняет обновление ежедневной вселенной (обёртка)."""
        async with self.sessionmaker() as session:
            await update_verse(session)
            await RedisRequests(get_redis()).clear_all_shop()

    async def _update_stats(self):
        """Периодическое обновление сообщения со статистикой."""
        if self.stats_chat_id is None or self.stats_message_id is None:
            logger.warning("Целевое сообщение для статистики не задано, пропуск обновления.")
            return
        async with self.sessionmaker() as session:
            await edit_stats(session, self.bot, self.stats_chat_id, self.stats_message_id)

    async def full_update(self):
        """Комплексное ежедневное обновление: вселенная, бэкап, VIP-открытия, кланы, пользователи."""
        logger.info("Запуск комплексного ежедневного обновления...")
        try:
            await self._run_update_verse()
            logger.info("Ежедневная вселенная обновлена.")
        except Exception as e:
            logger.exception(f"Ошибка при обновлении вселенной: {e}")

        async with self.sessionmaker() as session:

            try:
                await add_free_opens(session)
                logger.info("Бесплатные открытия добавлены VIP-пользователям.")
            except Exception as e:
                logger.exception(f"Ошибка при добавлении бесплатных открытий: {e}")

            try:
                await clan_rebalance(session)
                logger.info("Ребаланс кланов выполнен.")
            except Exception as e:
                logger.exception(f"Ошибка при ребалансе кланов: {e}")

            try:
                await update_info_users(self.bot, session)
                logger.info("Информация о пользователях обновлена.")
            except Exception as e:
                logger.exception(f"Ошибка при обновлении информации пользователей: {e}")

        logger.info("Комплексное ежедневное обновление завершено.")

    def setup_jobs(self) -> None:
        """Настраивает все периодические задачи планировщика."""
        sdl = self.scheduler

        # 1. Комплексное обновление каждый день в 00:00 (полночь)
        sdl.add_job(
            self.full_update,
            CronTrigger(hour=0, minute=0, timezone=MSK_TIMEZONE),
            id="daily_full_update",
            replace_existing=True,
            max_instances=1
        )

        # 2. Обновление статистики каждые 5 минут
        sdl.add_job(
            self._update_stats,
            "interval",
            minutes=5,
            id="stats_update",
            replace_existing=True,
            max_instances=1
        )

        sdl.add_job(
            create_backup,
            CronTrigger(hour=4, minute=0, timezone=MSK_TIMEZONE),
            id="backup_only",
            replace_existing=True,
            max_instances=1
        )

        logger.info("Все задачи планировщика настроены.")

    def start(self) -> None:
        """Запускает планировщик."""
        if not self.scheduler.running:
            # Убедимся, что задачи настроены перед запуском
            if not self.scheduler.get_jobs():
                self.setup_jobs()
            self.scheduler.start()
            logger.info("Планировщик запущен.")
        else:
            logger.warning("Планировщик уже запущен.")

    def shutdown(self) -> None:
        """Останавливает планировщик (корректное завершение)."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Планировщик остановлен.")