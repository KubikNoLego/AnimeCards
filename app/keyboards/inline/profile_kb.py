from aiogram.utils.keyboard import InlineKeyboardBuilder

from .CallbackDatas import Pagination

async def user_panel(user_id: int):

    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Изменить баланс", callback_data=f"adm_bal_{user_id}")
    builder.button(text="⭐ VIP", callback_data=f"adm_vip_{user_id}")
    builder.button(text="📋 Инвентарь", callback_data=f"adm_inv_{user_id}")
    builder.adjust(2, 1)

    return builder.as_markup()

async def profile_keyboard(has_describe: bool, vip: bool):
    builder = InlineKeyboardBuilder()

    builder.button(text="📦 Инвентарь", callback_data=Pagination(p=1).pack())
    
    if not vip:
        builder.button(text="💰 Купить VIP", callback_data="buy_vip")

    builder.button(text="🖋️ Сменить подпись",callback_data="change_describe")
    if has_describe:
        builder.button(text="❌ Удалить подпись",
                    callback_data="delete_describe",style = "danger")

    builder.adjust(1)

    return builder.as_markup()

async def vip_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Купить VIP за 150 ⭐", callback_data="buy_vip")
    builder.adjust(1)

    return builder.as_markup()