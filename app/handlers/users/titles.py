from aiogram import Router,F
from aiogram.types import Message, CallbackQuery, InputRichMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.requests import DB
from app.filters import Private
from app.messages import MText
from app.services.TitleService import TitleService
from app.keyboards.inline.title_kb import get_title_keyboard, spin_again
from app.utils.constants import TITLE_SPIN_PRICE
from app.services.PaginationService import TitlePagination
from app.keyboards.inline.datas import TitlePagination as TP


router = Router()


@router.message(F.text == "⚜️ Титулы", Private())
async def _(message: Message, session: AsyncSession):
    user = await DB(session).user.get_user(message.from_user.id)
    if not user:
        return
    
    bonuses = (TitleService.format_buffs(user.profile.title)
                    .replace('\n', '<br>'))
    keyboard = get_title_keyboard()
    await message.answer_rich(InputRichMessage(
        html= MText.get("titles_message").format(
        title=user.profile.title.name, rarity=user.profile.title.rarity.name, 
        buffs=bonuses,
        price=TITLE_SPIN_PRICE)),
        reply_markup=keyboard)

@router.callback_query(F.data == "open_title")
async def open_title_callback(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id


    try:
        title = await TitleService.open_title(session, user_id)
        bonuses = TitleService.format_buffs(title)
        await callback.message.answer(MText.get("title_opened").format(
            bonuses = bonuses,
            title = title.name
        ),
        reply_markup=spin_again())

    except ValueError as _e:
        await callback.answer(str(_e))

    finally:
        await callback.message.delete()

@router.callback_query(TP.filter())
async def _(callback: CallbackQuery, callback_data: TP, session: AsyncSession):

    page = callback_data.p

    db = DB(session)
    user = await db.user.get_user(callback.from_user.id)

    if not user.unlocked_titles:
        await callback.answer("📖 У вас пока нет разблокированных титулов")
        return

    if page >= len(user.unlocked_titles):
        page = len(user.unlocked_titles)

    title = user.unlocked_titles[page-1]

    pg = TitlePagination(page, user.unlocked_titles)
    kb = await pg.keyboard()

    await callback.message.edit_text(f"🏆 <b>{title.name}</b> ({title.rarity.name})\n\n<b>Бонусы:</b>\n<blockquote>{TitleService.format_buffs(title)}</blockquote>", reply_markup=kb)

@router.callback_query(F.data.contains("select_title:"))
async def _(callback: CallbackQuery, session: AsyncSession):
    
    title_id = callback.data.split(":")[1]
    try:
        await TitleService.update_user_title(session,
                                            callback.from_user.id,
                                            int(title_id))
        
        await callback.message.delete()
        await callback.answer("✅ Выбранный титул установлен", show_alert=True)

    except ValueError as _ex:
        
        await callback.answer(str(_ex), show_alert=True)