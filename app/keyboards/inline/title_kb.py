from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_title_keyboard() -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для работы с титулами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Открыть титул (250 ¥)", callback_data="open_title")
        ],
        [
            InlineKeyboardButton(text="📖 Информация о титулах", callback_data="title_info")
]
    ])
    return keyboard