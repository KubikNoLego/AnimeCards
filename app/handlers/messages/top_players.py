from aiogram import Router,F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.messages import MText
from db import DB


router = Router()


@router.message(F.text == "🏆 Топ игроков", Private())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        # Получаем топ игроков по балансу (10 человек)
        top_players_balance = await db.get_top_players_by_balance()
        text_balance = MText.top_players_formatter(top_players_balance,
                                                user.id)

        # Отправляем только топ по балансу
        await message.answer(text_balance, disable_notification=True,
                            disable_web_page_preview=True)
    else:
        text = MText.get("not_user").format(name=message.from_user.full_name)
        await message.reply(text)
