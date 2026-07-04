from collections import Counter
from datetime import datetime, timedelta
import time

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message, InputRichMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card
from app.filters import Private
from app.keyboards.inline.cards import roll_season_banner_amount_kb, roll_standard_banner_kb
from app.keyboards.inline.datas import RollSeasonBanner, RollSeasonBannerA
from app.messages import MText
from app.services.GachaService import GachaService
from app.services.BuffsService import BuffService
from app.keyboards import banners_select
from app.database import DB
from app.utils.constants import COOLDOWN, MSK_TIMEZONE, RARITY_EMOJIES, SEASON_ROLL_COST, SHINY_CHANCE
from app.utils.duration import format_duration
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
    
    await message.answer_rich(InputRichMessage(html=MText.get("banners_menu").format(chance=SHINY_CHANCE*100)), reply_markup=
                                        banners_select())

@router.callback_query(F.data == "standard_banner")
async def _(callback_query: CallbackQuery, session: AsyncSession):

    db = DB(session)

    user = await db.user.get_user(callback_query.from_user.id)
    buffs = await BuffService.calculate_buffs(user)

    pities = await GachaService._get_pity(session,1,user.id)
    daily_verse = await db.verse.get_daily_verse()

    pities_text = ''
    pities_text += f"<b>{RARITY_EMOJIES.get("S", "S")} {pities.s} / 30</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SR", "SR")} {pities.sr} / 50</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SSR", "SSR")} {pities.ssr} / 100</b>"

    hour = COOLDOWN - (1 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 0)
    target_time = user.last_open + timedelta(hours=hour)
    if buffs.cooldown:
        target_time -= timedelta(minutes=buffs.cooldown)
    delta = target_time - datetime.now(MSK_TIMEZONE)
    time = format_duration(delta)

    await callback_query.message.answer(MText.get("standart_banner").format(
                                                pities=pities_text,
                                                opens=user.free_standard_opens,
                                                time=(time
                                                    if time != "0 сек"
                                                    else "✅ Доступно" ),
                                                daily_verse=daily_verse.name), 
                                                reply_markup=
                                        roll_standard_banner_kb())
    await callback_query.message.delete()

@router.callback_query(F.data == "user_bonuses")
async def _(callback_query: CallbackQuery, session: AsyncSession):
    
    user = await DB(session).user.get_user(callback_query.from_user.id)

    buffs = await BuffService.calculate_buffs(user)

    await callback_query.message.answer(f"Ваши бонусы:\n{buffs}\n<i>Повышайте эти характеристики для большей выгоды!</i>")
    await callback_query.message.delete()

@router.callback_query(F.data == "roll_standard_banner")
async def _(callback_query: CallbackQuery, session: AsyncSession):

    db = DB(session)

    user = await db.user.get_user(callback_query.from_user.id)

    buffs = await BuffService.calculate_buffs(user)

    if GachaService.check_able_standard(user, buffs):

        card, shiny, yens_message = await GachaService.open_card(callback_query.from_user.id,
                                        session, 1)

        icon = card.icon_path(shiny)
        try:
            await callback_query.message.answer_photo(photo=FSInputFile(icon),
                                                caption=card.format(shiny))
        except Exception as _ex:
            await callback_query.message.answer(card.format(shiny))

        finally:
            await callback_query.message.delete()

        if yens_message:
            await callback_query.message.answer(yens_message)
    
    else:

        await callback_query.message.answer(GachaService.nottime(user.last_open,
                                    buffs))

@router.message(Command("card"))
async def _(message: Message, session: AsyncSession):
    db = DB(session)

    user = await db.user.get_user(message.from_user.id)

    buffs = await BuffService.calculate_buffs(user)

    if GachaService.check_able_standard(user, buffs):

        card, shiny, yens_message = await GachaService.open_card(message.from_user.id,
                                        session, 1)

        icon = card.icon_path(shiny)
        try:
            await message.reply_photo(photo=FSInputFile(icon),
                                                caption=card.format(shiny))
        except Exception as _ex:
            await message.reply(card.format(shiny))

        if yens_message:
            await message.reply(yens_message)
    
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
    pities_text += f"<b>{RARITY_EMOJIES.get("S", "S")} {pities.s} / 30</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SR", "SR")} {pities.sr} / 50</b>"
    pities_text += f"\n<b>{RARITY_EMOJIES.get("SSR", "SSR")} {pities.ssr} / 100</b>"

    cards = "\n".join([
        f"<b>{RARITY_EMOJIES.get("SSR", "SSR")} {bannercard.card.name}</b>" 
        for bannercard in banner.cards])

    await callback_query.message.answer_photo(
                        FSInputFile(f"app/assets/banners/{banner.name}.png"),
                                caption = MText.get("season_banner").format(
                                                banner_name = banner.name,
                                                cards = cards,
                                                pities = pities_text, 
                                                free_opens = user.free_season_opens,
                                                cost=SEASON_ROLL_COST), 
                                                reply_markup=
                                        roll_season_banner_amount_kb())
    await callback_query.message.delete()
    
@router.callback_query(RollSeasonBannerA.filter())
async def _(callback_query: CallbackQuery, callback_data: RollSeasonBannerA,
                                session: AsyncSession):
    amount = callback_data.amount
    db = DB(session)

    banner = await db.card.get_season_banner()
        
    user = await db.user.get_user(callback_query.from_user.id)
    can_open = GachaService.check_able_season(user, amount)

    await callback_query.message.delete()
        
    if amount == 1 and can_open:

        card, shiny = await GachaService.open_card(
            callback_query.from_user.id, session, banner.id)
            
        icon = card.icon_path(shiny)
        try:
            await callback_query.message.answer_photo(
                                                photo=FSInputFile(icon), 
                                                caption=card.format(shiny))
        except Exception as _ex:
            await callback_query.message.answer(card.format(shiny))
        finally:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
        
    elif amount > 1 and can_open:
        draft_id = int(time.time())
        await callback_query.bot.send_rich_message_draft(
            callback_query.from_user.id,draft_id, InputRichMessage(
                html=MText.get("card_open_draft1")
            )
        )
        cards = await GachaService.open_cards(callback_query.from_user.id,
                                            session,
                                            amount)
        cards_names_list = format_cards_to_lines(cards)
        await callback_query.bot.send_rich_message_draft(
            callback_query.from_user.id,draft_id, InputRichMessage(
                html=MText.get("card_open_draft2").format(
                    cards=cards_names_list.replace("\n","<br>"))
            )
        )
        image = generate_cards_image(cards)
        await callback_query.message.answer_photo(
            FSInputFile(image),
            caption=f"<b>Вы получили:</b>\n\n<blockquote>{cards_names_list}</blockquote>")
        
        await callback_query.bot.send_rich_message_draft(
            callback_query.from_user.id,draft_id, InputRichMessage(
                html="<h1>✅ Открытие завершено</h1>"
                )
            )
        
    else:
        await callback_query.answer("У вас нехватает ¥", show_alert=True)