from datetime import datetime, timedelta

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import VipSubscription
from app.messages import MText
from app.database import DB, PromoUsers
from app.utils.constants import MSK_TIMEZONE


router = Router()


@router.message(Command("promo","промо","промокод",prefix=".",ignore_case=True))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    if not command.args:
        await message.reply(MText.get("input_promocode"))
        return
    
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    
    if not user:
        await message.reply(MText.get("user_not_found_short"))
        return

    promo = await db.promo.get_promo(command.args)

    if not promo or not promo.is_active:
        await message.reply(MText.get("promo_expired"))
        return

    existing_usage = await session.scalar(
        select(PromoUsers)
        .filter_by(user_id=user.id, promo_id=promo.id)
    )

    if existing_usage:
        await message.reply(MText.get('u_already_use_this_promo'))
        return
    
    rewards = []
    for key, value in promo.reward.items():
        
        match key:
            case "vip":
                if user.vip:
                    user.vip.end_date += timedelta(days=value)
                new_vip = VipSubscription(
                    user_id = user.id,
                    start_date = datetime.now(MSK_TIMEZONE),
                    end_date = datetime.now(MSK_TIMEZONE) + timedelta(days=value)
                    )
                user.vip = new_vip
                rewards.append(f"💎 VIP на <b>{value} {("день"
                    if value == 1 else "дня" if value <= 4 else "дней")}</b>")

            case "luck_boost":
                user.luck_boosts += value
                rewards.append(f"🍀 <b>{value}</b> {"буст" if value == 1 else "бустов"} удачи")

            case "yen_boost":
                user.yen_boosts += value
                rewards.append(f"💰 <b>{value}</b> {"буст" if value == 1 else "бустов"} йен")

            case "yen":
                user.balance += value
                rewards.append(f"👛 <b>{value}</b> йен")

            case "free_standard_opens":
                user.free_standard_opens += value
                rewards.append(f"🎟️ <b>{value}</b> стандартных круток")
            
            case "free_season_opens":
                user.free_season_opens += value
                rewards.append(f"🎫 <b>{value}</b> cезонных круток")

    new_usage = PromoUsers(user_id=user.id, promo_id=promo.id)
    session.add(new_usage)

    await session.commit()

    await message.reply(MText.get("success_used_promo").format(rewards="\n".join(rewards)))
    

    
    
