from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.inline.datas import TitlePagination
from app.utils.constants import TITLE_SPIN_PRICE

def get_title_keyboard() -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для работы с титулами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🎴 Открыть титул ({TITLE_SPIN_PRICE} ¥)", callback_data="open_title")
        ],
        [
            InlineKeyboardButton(text="📖 Коллекция", callback_data=TitlePagination(p=1).pack())
]
    ])
    return keyboard

def spin_again():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="🔁 Открыть ещё раз", callback_data="open_title")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="titles_shop")]])
