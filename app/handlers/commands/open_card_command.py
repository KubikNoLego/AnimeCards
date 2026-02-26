from datetime import datetime,timedelta
import math

from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.messages import MText
from app.func import MSK_TIMEZONE, random_card
from db import DB


router = Router()
user_card_opens = []


@router.message(Command("card"))
async def _(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_id in user_card_opens:
        await message.reply(MText.get("wait"))
        return

    try:
        
        user_card_opens.append(user_id)
        db = DB(session)
        user = await db.get_user(user_id)
            
        if not user:
            await message.reply(MText.get("not_registered"))
            return
        
        last_open = user.last_open

        if last_open.tzinfo is None:
            last_open = last_open.replace(tzinfo=MSK_TIMEZONE)
            
        hour = 2 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 3

        if (last_open + timedelta(hours=hour) <= datetime.now(MSK_TIMEZONE)) or user.free_open:
            card = await random_card(session,user.pity)
            text = MText.get("card").format(name=card.name,
                                            verse=card.verse_name,
                                            rarity=card.rarity_name,
                                            value=card.value if not user.vip else f"{card.value} (+{math.ceil(card.value * 0.1)})")
            text = text + "\n\n✨ Shiny" if card.shiny else text
            
            await message.reply_photo(FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)
            if card not in user.inventory:
                user.inventory.append(card)
            match user.pity:
                case _ if user.pity <= 0:
                    user.pity = 100                    
                case _:
                    user.pity -= 1
            if user.free_open:
                user.free_open -= 1
            else:
                user.last_open = datetime.now(MSK_TIMEZONE)
            added_sum = int(card.value + (math.ceil(card.value * 0.1) if user.vip else 0))
            user.balance += added_sum
            if user.clan_member:
                user.clan_member.contribution += int(added_sum*0.3)
                user.clan_member.clan.balance += int(added_sum*0.3)
            await session.commit()
        else:
            text = MText.nottime(user.last_open)
            await message.reply(text)

    finally:
        # Убираем пользователя из списка после завершения (даже если была ошибка)
        if user_id in user_card_opens:
            user_card_opens.remove(user_id)