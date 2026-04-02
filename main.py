import asyncio

from loguru import logger

from config import config
from loader import setup_logger, setup_dispatcher
from bot import create_bot, create_dispatcher
from db import Base, create_sessionmaker, create_engine
from app.func.daily_updates import (
    _daily_coordinator,
    _edit_stats
)

setup_logger()

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

    # Запуск ежедневных обновлений в фоновом режиме
    global _daily_coordinator_task, _edit_stats_task
    
    _daily_coordinator_task = asyncio.create_task(_daily_coordinator(bot, sessionmaker))
    
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

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
