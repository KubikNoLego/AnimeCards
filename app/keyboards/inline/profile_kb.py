from aiogram.utils.keyboard import InlineKeyboardBuilder

from .datas import Pagination

async def user_panel(user_id: int):

    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Изменить баланс", callback_data=f"adm_bal_{user_id}")
    builder.button(text="⭐ VIP", callback_data=f"adm_vip_{user_id}")
    builder.button(text="📋 Инвентарь", callback_data=f"adm_inv_{user_id}")
    builder.button(text="", callback_data=f"adm_inv_{user_id}")
    builder.adjust(2, 1)

    return builder.as_markup()

async def profile_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(text="📦 Инвентарь", callback_data=Pagination(p=1).pack())
    builder.button(text="🔗 Реферальная ссылка", callback_data="referral_link")

    builder.adjust(1)

    return builder.as_markup()