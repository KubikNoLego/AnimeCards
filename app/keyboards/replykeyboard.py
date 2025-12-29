from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from random import randint

async def main_kb():
    buttons = ["🌐 Открыть карту","👤 Профиль"]
    builder = ReplyKeyboardBuilder()
    [builder.button(text=item) for item in buttons]
    builder.adjust(2)

    return builder.as_markup(resize_keyboard=True,input_field="Привет!" if randint(1,1000) == 777 else "...")