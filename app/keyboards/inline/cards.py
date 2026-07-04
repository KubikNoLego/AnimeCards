from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Banner
from app.keyboards.inline.datas import RollSeasonBanner, RollSeasonBannerA

def banners_select():

    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Стандартный", callback_data=f"standard_banner")
    builder.button(text="🌸 Сезонный", callback_data=f"season_banner")
    builder.button(text="➕ Бонусы", callback_data=f"user_bonuses")

    builder.adjust(2,1)

    return builder.as_markup()

def roll_standard_banner_kb():

    builder = InlineKeyboardBuilder()
    builder.button(text="Крутить", callback_data=f"roll_standard_banner")

    return builder.as_markup()

def roll_season_banner_amount_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Крутить 1x", callback_data=RollSeasonBannerA(amount= 1))
    builder.button(text="Крутить 10x", callback_data=RollSeasonBannerA(amount=10))
    
    return builder.as_markup()