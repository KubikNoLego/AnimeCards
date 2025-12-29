from aiogram import BaseMiddleware
from aiogram.types import Message

from sqlalchemy.ext.asyncio import async_sessionmaker

class DBSessionMiddleware(BaseMiddleware):
    def __init__(self,sessionmaker:async_sessionmaker):
        self._sessionmaker = sessionmaker

    async def __call__(self, handler, event, data):
        async with self._sessionmaker() as session:
            data["session"] = session
            return await handler(event,data)