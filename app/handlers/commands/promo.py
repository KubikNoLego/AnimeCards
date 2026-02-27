from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.messages import MText
from db import DB, PromoUsers


router = Router()


@router.message(Command("promo",prefix="."))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    if not command.args:
        await message.reply(MText.get("input_promocode"))
        return
    
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.reply(MText.get("user_not_found_short"))
        return

    promo = await db.get_promo(command.args)

    if not promo:
        await message.reply(MText.get("promo_expired"))
        return

    existing_usage = await session.scalar(
        select(PromoUsers)
        .filter_by(user_id=user.id, promo_id=promo.id)
    )

    if existing_usage:
        await message.reply(MText.get('u_already_use_this_promo'))
        return

    user.balance += promo.reward

    new_usage = PromoUsers(user_id=user.id, promo_id=promo.id)
    session.add(new_usage)

    await session.commit()

    await message.reply(MText.get("success_used_promo").format(reward=promo.reward))
    

    
    
