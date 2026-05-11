from aiogram import Router,F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.requests import DB
from app.filters import Private
from app.messages import MText
from app.services.random_title import open_title
from app.utils.enums.title_enums import TitleOpen
from app.utils.title import format_buffs
from app.keyboards.inline.title_kb import get_title_keyboard


router = Router()


@router.message(F.text == "⚜️ Титулы", Private())
async def _(message: Message, session: AsyncSession):
    user = await DB(session).user.get_user(message.from_user.id)
    if not user:
        return

    keyboard = get_title_keyboard()
    await message.answer(MText.get("title_message_text").format(
        title=user.profile.title.title, rarity=user.profile.title.rarity.name, buffs=format_buffs(user.profile.title)),
        reply_markup=keyboard)

@router.callback_query(F.data == "open_title")
async def open_title_callback(callback: CallbackQuery, session: AsyncSession):
    """
    Обработчик callback для открытия титула
    """
    user_id = callback.from_user.id

    result = await open_title(session, user_id)

    match result:
        case TitleOpen.NOT_REGISTERED:
            await callback.answer("❌ Вы не зарегистрированы", show_alert=True)
        case TitleOpen.NOT_ENOUGH_YENS:
            await callback.answer("❌ Недостаточно йен (нужно 250 ¥)", show_alert=True)
        case TitleOpen.ERROR:
            await callback.answer("❌ Ошибка при открытии титула", show_alert=True)
        case _:
            title = result
            await callback.message.answer(f"🎉 <b>Новый титул получен!</b>\n\n<b>🏆 {title.title}</b>\n\n<b>Бонусы:</b>\n{format_buffs(title)}")
            await callback.answer("🎉 Титул успешно открыт!")

@router.callback_query(F.data == "title_info")
async def title_info_callback(callback: CallbackQuery):
    """
    Обработчик callback для информации о титулах
    """
    info_text = MText.get("title_info_text")

    await callback.message.answer(info_text)
    await callback.answer()
