from aiogram import Router,F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.messages import MText
from app.keyboards import trade_kb_pagination
from db import DB, User


router = Router()


@router.message(F.text == "🔁 Трейды", Private())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user: User = await db.get_user(message.from_user.id)

    if len(user.inventory) > 0:
        await message.answer(MText.get("trade_message"),reply_markup=await trade_kb_pagination())