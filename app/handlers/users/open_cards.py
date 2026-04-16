import math
import asyncio
from collections import defaultdict

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, ReactionTypeEmoji
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.messages import MText
from app.services.random_card import open_card
from app.utils.enums.open_card_enums import CardOpen
from app.utils.card_formater import format_open_card, nottime
from app.database import DB


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
        user = await db.user.get_user(user_id)

        match result:
            case CardOpen.NOT_REGISTERED:
                await message.reply(MText.get("not_registered"))
            case CardOpen.NOT_TIME:
                await message.reply(nottime(user.last_open))
            case CardOpen.ERROR:
                await message.reply("Произошла ошибка при открытии карты.")
            case Card:
                card = result

                text = await format_open_card(card, user)

                await message.reply_photo(
                    photo=FSInputFile(path=f"app/assets/cards/{card.verse.name}/{card.icon}"),
                    caption=text
                )


@router.message(Command("card"))
async def _(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_card_opens[user_id].locked():
        await message.reply(MText.get("wait"))
        return
    
    
    async with user_card_opens[user_id]:

        # Параллельно обрабатываем открытие карты
        result = await open_card(session,user_id)

        db = DB(session)
        user = await db.user.get_user(user_id)

        match result:

            case CardOpen.NOT_REGISTERED:
                await message.reply(MText.get("not_registered"))
            case CardOpen.NOT_TIME:
                await message.reply(nottime(user.last_open))
                await message.react([ReactionTypeEmoji(emoji="😴")])
            case CardOpen.ERROR: pass
            case Card:
                card = result

                text = await format_open_card(card, user)

                await message.reply_photo(
                    photo=FSInputFile(path=f"app/assets/cards/{card.verse.name}/{card.icon}"),
                    caption=text
                )

                await message.react([ReactionTypeEmoji(emoji="💘")])