import asyncio
from collections import defaultdict

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, InputMediaVideo, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.keyboards.inline.cards import roll_standard_banner_kb
from app.messages import MText
from app.services.GachaService import GachaService, LuckService
from app.keyboards import banners_select
from app.database import DB


router = Router()
user_card_opens = defaultdict(asyncio.Lock)


@router.message(F.text == "🎴 Баннеры", Private())
async def _(message: Message, session: AsyncSession):
    
    await message.answer(MText.get("banners_menu"), reply_markup=
                                        banners_select())

@router.callback_query(F.data == "standard_banner")
async def _(callback_query: CallbackQuery, session: AsyncSession):

    user = await DB(session).user.get_user(callback_query.from_user.id)
    buffs = await LuckService.calculate_buffs(user)

    await callback_query.message.answer(f"{buffs}", reply_markup=
                                        roll_standard_banner_kb())
    await callback_query.message.delete()

@router.callback_query(F.data == "roll_standard_banner_1")
async def _(callback_query: CallbackQuery, session: AsyncSession):

    db = DB(session)

    user = await db.user.get_user(callback_query.from_user.id)

    buffs = await LuckService.calculate_buffs(user)

    if GachaService.check_able_standard(user, buffs):

        card, shiny = await GachaService.open_card(callback_query.from_user.id,
                                        session, 1, None)
    
        icon = card.icon_path(shiny)
        try:
            await callback_query.message.answer_photo(photo=FSInputFile(icon), 
                                                caption=card.format(shiny))
        except Exception as _ex:
            await callback_query.message.answer(card.format(shiny))

        finally:
            await callback_query.message.delete()

        added = await GachaService.add_yens(user, card, shiny, session)
        if added:
            await callback_query.message.answer(added)
    
    else:

        await callback_query.message.answer(GachaService.nottime(user.last_open,
                                    buffs))

@router.message(Command("card"))
async def _(message: Message, session: AsyncSession):
    db = DB(session)

    user = await db.user.get_user(message.from_user.id)

    buffs = await LuckService.calculate_buffs(user)

    if GachaService.check_able_standard(user, buffs):

        card, shiny = await GachaService.open_card(message.from_user.id,
                                        session, 1, None)
    
        icon = card.icon_path(shiny)
        try:
            await message.reply_photo(photo=FSInputFile(icon), 
                                                caption=card.format(shiny))
        except Exception as _ex:
            await message.reply(card.format(shiny))

        added = await GachaService.add_yens(user, card, shiny, session)
        if added:
            await message.reply(added)
    
    else:

        await message.answer(GachaService.nottime(user.last_open,
                                    buffs))