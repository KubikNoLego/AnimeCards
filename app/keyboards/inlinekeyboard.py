from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class Pagination(CallbackData,prefix="p"):
    p: int
    a:int

async def pagination_keyboard(
    current_page: int,
    total_pages: int,
):
    
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