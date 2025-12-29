from aiogram import BaseMiddleware
from aiogram.types import Message

from sqlalchemy.ext.asyncio import async_sessionmaker
from loguru import logger

class DBSessionMiddleware(BaseMiddleware):
    def __init__(self,sessionmaker:async_sessionmaker):
        self._sessionmaker = sessionmaker

    async def __call__(self, handler, event, data):
        # Открываем сессию и явную транзакцию, чтобы
        # `.with_for_update()` работал корректно (требует транзакции).
        async with self._sessionmaker() as session:
            async with session.begin():
                data["session"] = session
                try:
                    return await handler(event, data)
                except Exception as exc:
                    # При исключении транзакция будет откатена автоматически.
                    logger.exception(f"Ошибка в обработчике, транзакция откатится: {exc}")
                    raise