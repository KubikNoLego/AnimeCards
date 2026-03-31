import math
import asyncio
from collections import defaultdict
from random import choice, randint

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message, ReactionTypeEmoji
from sqlalchemy.ext.asyncio import AsyncSession

from app.StateGroups.states import CardOpenFSM
from app.filters import Private
from app.messages import MText
from app.func import open_card, CardOpen
from app.func.consts import JOKES
from db.requests import DB


router = Router()
user_card_opens = defaultdict(asyncio.Lock)


@router.message(F.text == "🌐 Открыть карту", Private())
async def _(message: Message, session: AsyncSession, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_card_opens[user_id].locked():
        await message.reply(MText.get("wait"))
        return
    
    problem = MText.get_question(randint(1,10))
    await state.set_state(CardOpenFSM.answer)
    await state.set_data({"problem_id": problem['id']})
    await message.answer(f"Задача:\n<b>{problem["task"]}</b>\n\nНапишите ответ, чтобы открыть карту!")


@router.message(Command("card"))
async def _(message: Message, session: AsyncSession, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_card_opens[user_id].locked():
        await message.reply(MText.get("wait"))
        return
    
    problem = MText.get_question(randint(1,50))
    await state.set_state(CardOpenFSM.answer)
    await state.set_data({"problem_id": problem['id']})
    await message.answer(f"Задача:\n<b>{problem["task"]}</b>\n\nНапишите ответ, чтобы открыть карту!")

@router.message(CardOpenFSM.answer)
async def _(message: Message, session: AsyncSession, state: FSMContext):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    data = await state.get_data()
    problem = MText.get_question(data['problem_id'])

    if message.text.strip().lower() not in problem["accepted_answers"]:
        await state.clear()
        await message.reply(f"Ответ неверный\n{problem['explanation']}\nОтвет: {problem['correct_answer']}")
        return

    async with user_card_opens[user.id]:
        result = await open_card(session, user.id)

        match result:
            case CardOpen.NOT_REGISTERED:
                await message.reply(MText.get("not_registered"))
            case CardOpen.NOT_TIME:
                await message.reply(MText.nottime(user.last_open))
                await message.react([ReactionTypeEmoji(emoji="😴")])
            case CardOpen.ERROR:
                await message.reply("Произошла ошибка при открытии карты.")
            case CardOpen.JOCKER: 
                await message.reply_photo(photo=FSInputFile(path="app/icons/Blender.png"),caption=f"<b>BLENDER</b>\n\n🌐 Вселенная: <i>???</i>\n🎨 Редкость: <b>DIVINE</b>\n💰 Ценность: <b>-∞</b> ¥\n\n🍀 Гарант на Хроно: 0/100")
            case CardOpen.JOKE:
                await message.reply(choice(JOKES))
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

                await message.reply_photo(
                    photo=FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"),
                    caption=text
                )
    await state.clear()