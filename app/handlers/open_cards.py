import math
import asyncio
from collections import defaultdict

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, ReactionTypeEmoji
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.messages import MText
from app.func import open_card, CardOpen
from db.requests import DB


router = Router()
user_card_opens = defaultdict(asyncio.Lock)


@router.message(F.text == "🌐 Открыть карту", Private())
async def _(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_card_opens[user_id].locked():
        await message.reply(MText.get("wait"))
        return
    
    
    async with user_card_opens[user_id]:

        result = await open_card(session, user_id)

        db = DB(session)
        user = await db.get_user(user_id)

        match result:
            
            case CardOpen.NOT_REGISTERED:
                await message.answer(MText.get("not_registered"))
            case CardOpen.NOT_TIME:
                await message.answer(MText.nottime(user.last_open))
            case CardOpen.ERROR: pass
            case Card:
                card = result

                text = MText.get("card").format(name=card.name,
                                                verse=card.verse_name,
                                                rarity=card.rarity_name,
                                                value=(card.value
                                                    if not user.vip
                        else f"{card.value} (+{math.ceil(card.value * 0.1)})"))
                text = text + "\n\n✨ Shiny" if card.shiny else text
                text += MText.get("pity").format(pity=100-user.pity)

                await message.answer_photo(FSInputFile(
                path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)

@router.message(Command("card"))
async def _(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_card_opens[user_id].locked():
        await message.reply(MText.get("wait"))
        return
    
    
    async with user_card_opens[user_id]:

        result = await open_card(session, user_id)

        db = DB(session)
        user = await db.get_user(user_id)

        match result:
            
            case CardOpen.NOT_REGISTERED:
                await message.answer(MText.get("not_registered"))
            case CardOpen.NOT_TIME:
                await message.answer(MText.nottime(user.last_open))
                await message.react([ReactionTypeEmoji(emoji="😴")])
            case CardOpen.ERROR: pass
            case Card:
                card = result

                text = MText.get("card").format(name=card.name,
                                                verse=card.verse_name,
                                                rarity=card.rarity_name,
                                                value=(card.value
                                                    if not user.vip
                        else f"{card.value} (+{math.ceil(card.value * 0.1)})"))
                text = text + "\n\n✨ Shiny" if card.shiny else text
                text += MText.get("pity").format(pity=100-user.pity)

                await message.answer_photo(FSInputFile(
                path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)

                await message.react([ReactionTypeEmoji(emoji="💘")])
