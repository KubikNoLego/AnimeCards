from aiogram.utils.keyboard import InlineKeyboardBuilder

def banners_select():

    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Стандартный", callback_data=f"standard_banner")
    builder.button(text="🌸 Сезонный", callback_data=f"standard_banner")

    return builder.as_markup()

def roll_standard_banner_kb():

    builder = InlineKeyboardBuilder()
    builder.button(text="1x Крутить", callback_data=f"roll_standard_banner_1")
    builder.button(text="10x Крутить", callback_data=f"roll_standard_banner_10")

    return builder.as_markup()