from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from random import randint

class Pagination(CallbackData, prefix="p"):
    """Callback data for pagination buttons."""
    p: int
    a: int

async def main_kb():
    """Create main reply keyboard.

    Returns:
        ReplyKeyboardMarkup with main buttons
    """
    buttons = ["🌐 Открыть карту", "👤 Профиль"]
    builder = ReplyKeyboardBuilder()
    [builder.button(text=item) for item in buttons]
    builder.adjust(2)

    return builder.as_markup(resize_keyboard=True, input_field="Привет!" if randint(1, 1000) == 777 else "...")

async def pagination_keyboard(current_page: int, total_pages: int):
    """Create pagination inline keyboard.

    Args:
        current_page: Current page number
        total_pages: Total number of pages

    Returns:
        InlineKeyboardMarkup with pagination buttons
    """
    builder = InlineKeyboardBuilder()

    prev_100_active = current_page > 100
    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10
    next_100_active = current_page <= total_pages - 100

    buttons = []

    if prev_100_active:
        buttons.append(("««", Pagination(p=current_page, a=1).pack()))

    if prev_10_active:
        buttons.append(("‹", Pagination(p=current_page, a=2).pack()))

    if prev_1_active:
        buttons.append(("←", Pagination(p=current_page, a=3).pack()))

    buttons.append((f"{current_page}/{total_pages}", "pass"))

    if next_1_active:
        buttons.append(("→", Pagination(p=current_page, a=4).pack()))

    if next_10_active:
        buttons.append(("›", Pagination(p=current_page, a=5).pack()))

    if next_100_active:
        buttons.append(("»»", Pagination(p=current_page, a=6).pack()))

    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(len(buttons))

    return builder.as_markup()
