from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database.models import User

class UpdateUserMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(self, handler, event: TelegramObject, data: dict):
        tg_user: TgUser | None = data.get("event_from_user")

        if tg_user:
            async with self.sessionmaker() as session:
                user = await session.get(User, tg_user.id)

                if user:
                    changed = (
                        user.username != tg_user.username
                        or user.name != tg_user.full_name)

                    if changed:
                        user.username = tg_user.username
                        user.name = tg_user.full_name
                        await session.commit()

        return await handler(event, data)