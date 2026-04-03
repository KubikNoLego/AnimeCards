import argparse
import asyncio
import sys

from loguru import logger

# Импортируем config из app.config
from app.config import config

# Импортируем из app
from app.loader import setup_logger, setup_dispatcher
from app.bot import create_bot, create_dispatcher
from app.database import Base, create_sessionmaker, create_engine
from app.services.daily_updates import (
    _daily_coordinator,
    _edit_stats
)


def parse_args() -> argparse.Namespace:
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Telegram бот для управления карточками аниме",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m app.main              # Запуск в обычном режиме
  python -m app.main --debug      # Запуск в режиме отладки
  python -m app.main -d           # Короткая форма для debug режима
        """
    )
    
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Запуск в режиме отладки (подробные логи, отключены фоновые задачи)"
    )
    
    return parser.parse_args()


def main() -> None:
    """Точка входа приложения."""
    args = parse_args()
    
    # Настройка логирования с учетом debug режима
    setup_logger(debug=args.debug)
    
    if args.debug:
        logger.info("Запуск в режиме отладки (debug mode)")
        logger.warning("Фоновые задачи (ежедневные обновления, статистика) отключены")
    
    bot = create_bot(config)
    dp = create_dispatcher(config)
    
    engine = create_engine(config)
    sessionmaker = create_sessionmaker(engine)
    
    # Глобальные переменные для хранения ссылок на фоновые задачи
    _daily_coordinator_task = None
    _edit_stats_task = None
    
    setup_dispatcher(dp, sessionmaker)
    
    @dp.startup()
    async def on_startup():
        await bot.delete_webhook(True)
        
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        
        # Запуск фоновых задач только в обычном режиме (не debug)
        if not args.debug:
            global _daily_coordinator_task, _edit_stats_task
            
            _daily_coordinator_task = asyncio.create_task(
                _daily_coordinator(bot, sessionmaker)
            )
            
            # Запуск обновления статистики
            try:
                _edit_stats_task = asyncio.create_task(
                    _edit_stats(
                        bot=bot,
                        chat_id=config.CHAT_ID,
                        message_id=config.MESSAGE_ID,
                        db_sessionmaker=sessionmaker,
                        interval=600
                    )
                )
                logger.info("Запущено обновление статистики")
            except Exception as e:
                logger.warning(f"Не удалось запустить обновление статистики: {e}")
        else:
            logger.info("Фоновые задачи пропущены (debug режим)")
        
        logger.success("Бот успешно запущен")
    
    @dp.shutdown()
    async def on_shutdown():
        # Отменяем фоновые задачи при завершении работы
        if _daily_coordinator_task and not _daily_coordinator_task.done():
            _daily_coordinator_task.cancel()
            try:
                await _daily_coordinator_task
            except asyncio.CancelledError:
                pass
        
        if _edit_stats_task and not _edit_stats_task.done():
            _edit_stats_task.cancel()
            try:
                await _edit_stats_task
            except asyncio.CancelledError:
                pass
        
        await engine.dispose()
        logger.info("Бот отключён")
    
    # Запуск поллинга
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()