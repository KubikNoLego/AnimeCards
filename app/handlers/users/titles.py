from aiogram import Router,F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.requests import DB
from app.filters import Private
from app.messages import MText
from app.utils.title import format_buffs


router = Router()


@router.message(F.text == "⚜️ Титулы", Private())
async def _(message: Message, session: AsyncSession):
    user = await DB(session).user.get_user(message.from_user.id)
    if not user:
        return
    await message.answer(MText.get("title_message_text").format(
        title=user.profile.title.title, buffs=format_buffs(user.profile.title)))