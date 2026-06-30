from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.services.updates import (
    update_verse,
    add_free_opens,
    clan_rebalance,
    create_backup,
    edit_stats,
    remove_expired_vip_subscriptions,
)
from app.utils.constants import MSK_TIMEZONE


class SchedulerManager:
    def __init__(self, bot, sessionmaker):
        self.bot = bot
        self.sessionmaker = sessionmaker
        self.scheduler = AsyncIOScheduler(timezone=MSK_TIMEZONE)

        self.stats_chat_id: int | None = None
        self.stats_message_id: int | None = None

    def set_stats_target(self, chat_id: int, message_id: int) -> None:
        self.stats_chat_id = chat_id
        self.stats_message_id = message_id
    
    async def full_update(self) -> None:
        """Ежедневное обновление."""

        logger.info("Запуск ежедневного обновления...")

        async with self.sessionmaker() as session:

            try:
                await update_verse(session)
            except Exception:
                logger.exception("Ошибка обновления ежедневной вселенной.")

            try:
                await add_free_opens(session)
            except Exception:
                logger.exception("Ошибка выдачи бесплатных открытий.")

            try:
                await clan_rebalance(session)
            except Exception:
                logger.exception("Ошибка ребаланса кланов.")

        logger.info("Ежедневное обновление завершено.")

    async def update_stats(self) -> None:
        """Обновление сообщения со статистикой."""

        if self.stats_chat_id is None or self.stats_message_id is None:
            return

        async with self.sessionmaker() as session:
            success = await edit_stats(
                bot=self.bot,
                chat_id=self.stats_chat_id,
                message_id=self.stats_message_id,
                session=session,
            )

        if not success:
            logger.warning("Обновление статистики отключено.")
            self.stats_chat_id = None
            self.stats_message_id = None

    async def check_expired_vip(self) -> None:
        """Удаление просроченных VIP."""

        async with self.sessionmaker() as session:
            try:
                removed = await remove_expired_vip_subscriptions(
                    session=session,
                    bot=self.bot,
                )

                if removed:
                    logger.info(f"Удалено {removed} просроченных VIP.")

            except Exception:
                logger.exception("Ошибка проверки VIP.")

    def setup_jobs(self) -> None:
        sdl = self.scheduler

        # Ежедневное обновление
        sdl.add_job(
            self.full_update,
            CronTrigger(hour=0, minute=0, timezone=MSK_TIMEZONE),
            id="daily_update",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )

        # Проверка VIP
        sdl.add_job(
            self.check_expired_vip,
            "interval",
            minutes=15,
            id="vip_check",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )

        # Обновление статистики
        sdl.add_job(
            self.update_stats,
            "interval",
            minutes=5,
            id="stats_update",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )

        # Бэкап
        sdl.add_job(
            create_backup,
            CronTrigger(hour=4, minute=0, timezone=MSK_TIMEZONE),
            id="backup",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )

        logger.info("Планировщик настроен.")

    def start(self) -> None:
        if self.scheduler.running:
            logger.warning("Планировщик уже запущен.")
            return

        if not self.scheduler.get_jobs():
            self.setup_jobs()

        self.scheduler.start()
        logger.info("Планировщик запущен.")

    def shutdown(self) -> None:
        if not self.scheduler.running:
            return

        self.scheduler.shutdown(wait=True)
        logger.info("Планировщик остановлен.")