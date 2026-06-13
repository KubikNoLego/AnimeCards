from collections import Counter

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card
from app.filters import Private
from app.keyboards.inline.cards import roll_season_banner_amount_kb, roll_season_banner_kb, roll_standard_banner_kb
from app.keyboards.inline.datas import RollSeasonBanner, RollSeasonBannerA
from app.messages import MText
from app.services.GachaService import GachaService, LuckService
from app.keyboards import banners_select
from app.database import DB
from app.utils.constants import RARITY_EMOJIES, SEASON_ROLL_COST
from app.utils.multiopen_utils import generate_cards_image

router = Router()

def format_cards_to_lines(cards: list[tuple[Card, bool]]):

    counter = Counter(cards)

    lines = []

    for (card, shiny), amount in counter.items():

        line = f"{RARITY_EMOJIES.get(card.rarity.name, card.rarity.name)}"
        line += f" {card.name}"
        line += " (✨ Shiny)" if shiny else ''

        if amount > 1:
            line += f" x{amount}"

        lines.append(line)
    
    return "\n".join(lines)


@router.message(F.text == "🎴 Баннеры", Private())
async def _(message: Message, session: AsyncSession):
    
    await message.answer(MText.get("banners_menu"), reply_markup=
                                        banners_select())

@router.callback_query(F.data == "standard_banner")
async def _(callback_query: CallbackQuery, session: AsyncSession):

    db = DB(session)

    user = await db.user.get_user(callback_query.from_user.id)
    buffs = await LuckService.calculate_buffs(user)

    pities = await GachaService._get_pity(session,1,user.id)

    pities_text = ''
    pities_text += f"<b>{RARITY_EMOJIES.get("S", "S")} {pities.s_pity} / 30</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SR", "SR")} {pities.sr_pity} / 50</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SSR", "SSR")} {pities.ssr_pity} / 100</b>"

    can_open = "✅ Доступно" if GachaService.check_able_standard(user, buffs) else "❌ Недоступно"

    await callback_query.message.answer(MText.get("standart_banner").format(
                                                pities=pities_text, 
                                                free_opens=user.free_open,
                                                can_open=can_open), 
                                                reply_markup=
                                        roll_standard_banner_kb())
    await callback_query.message.delete()

@router.callback_query(F.data == "user_bonuses")
async def _(callback_query: CallbackQuery, session: AsyncSession):
    
    user = await DB(session).user.get_user(callback_query.from_user.id)

    buffs = await LuckService.calculate_buffs(user)

    await callback_query.message.answer(f"Ваши бонусы:\n{buffs}\n<i>Повышайте эти характеристики для большей выгоды!</i>")
    await callback_query.message.delete()

@router.callback_query(F.data == "roll_standard_banner")
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
        
@router.callback_query(F.data == "season_banner")
async def _(callback_query: CallbackQuery, session: AsyncSession):
    db = DB(session)

    user = await db.user.get_user(callback_query.from_user.id)

    banner = await db.card.get_season_banner()

    pities = await GachaService._get_pity(session,banner.id,user.id)

    pities_text = ''
    pities_text += f"<b>{RARITY_EMOJIES.get("S", "S")} {pities.s_pity} / 30</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SR", "SR")} {pities.sr_pity} / 50</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SSR", "SSR")} {pities.ssr_pity} / 100</b>"

    cards = "\n".join([
        f"<b>{RARITY_EMOJIES.get("SSR", "SSR")} {bannercard.card.name}</b>" 
        for bannercard in banner.cards])

    await callback_query.message.answer_photo(
                        FSInputFile(f"app/assets/banners/{banner.name}.png"),
                                caption = MText.get("season_banner").format(
                                                banner_name = banner.name,
                                                cards = cards,
                                                pities = pities_text, 
                                                free_opens = user.free_open,
                                                cost=SEASON_ROLL_COST), 
                                                reply_markup=
                                        roll_season_banner_kb(banner))
    await callback_query.message.delete()

@router.callback_query(RollSeasonBanner.filter())
async def _(callback_query: CallbackQuery, callback_data: RollSeasonBanner,
                                                        session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(callback_query.from_user.id)
    card = await db.card.get_card(callback_data.card_id)

    free_opens_available = min(10, user.free_open)
    paid_cost_per_roll = SEASON_ROLL_COST

    rarity_emoji = RARITY_EMOJIES.get(card.rarity.name, card.rarity.name)

    message_text = f"🎯 <b>Вы выбрали карту:</b>\n"
    message_text += f"{rarity_emoji} <b>{card.name}</b>\n\n"

    message_text += f"💰 <b>Стоимость:</b>\n"
    message_text += f"• 1 открытие: {free_opens_available > 0 and 'БЕСПЛАТНО' or f'{paid_cost_per_roll} ¥'}\n"
    message_text += f"• 10 открытий: {paid_cost_per_roll * 10 - free_opens_available * paid_cost_per_roll} ¥ (с учетом бесплатных)\n\n"

    message_text += f"💎 <b>Ваш баланс:</b> {user.balance} ¥\n"
    message_text += f"🎁 <b>Бесплатных открытий:</b> {user.free_open}\n"

    await callback_query.message.answer(message_text,
            reply_markup=roll_season_banner_amount_kb(callback_data.card_id))
    await callback_query.message.delete()
    
@router.callback_query(RollSeasonBannerA.filter())
async def _(callback_query: CallbackQuery, callback_data: RollSeasonBannerA,
                                session: AsyncSession):
    card_id, amount = callback_data.card_id, callback_data.amount
    db = DB(session)

    banner = await db.card.get_season_banner()
    
    card_in_banner = False
    
    for bannercard in banner.cards:
        if bannercard.card_id == card_id:
            card_in_banner = True

    if card_in_banner:
        
        user = await db.user.get_user(callback_query.from_user.id)
        can_open = GachaService.check_able_season(user, amount)

        await callback_query.message.delete()
        
        if amount == 1 and can_open:

            card, shiny = await GachaService.open_card(
                callback_query.from_user.id, session, banner.id, card_id)
            
            icon = card.icon_path(shiny)
            try:
                await callback_query.message.answer_photo(
                                                    photo=FSInputFile(icon), 
                                                    caption=card.format(shiny))
            except Exception as _ex:
                await callback_query.message.answer(card.format(shiny))

            finally:
                await callback_query.message.delete()
        
        elif amount > 1 and can_open:
            wait_message = await callback_query.message.answer_animation(
                                                        FSInputFile(
                                                        "app/assets/open.mp4"))
        
            cards = await GachaService.open_cards(callback_query.from_user.id,
                                                session, card_id,
                                                amount)

            cards_names_list = format_cards_to_lines(cards)
            await callback_query.message.answer_photo(
                FSInputFile(generate_cards_image(cards)),
                caption=f"Вы получили:\n<blockquote>{cards_names_list}</blockquote>")
            await wait_message.delete()
            
        else:
            await callback_query.answer("У вас нехватает ¥", show_alert=True)