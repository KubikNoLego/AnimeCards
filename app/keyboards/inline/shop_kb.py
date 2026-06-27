from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import ShopItems, VipSubscription
from app.utils.constants import SHOP_ITEMS

from .datas import ShopItemCallback, VipPurchase


def shop_keyboard(purchased: set[ShopItems], vip: VipSubscription | None):
    """Создать инлайн-клавиатуру для магазина"""
    builder = InlineKeyboardBuilder()

    
    for item, (name, price) in SHOP_ITEMS.items():
        builder.button(
            text=f"✅ {name}" if item in purchased else f"{name} • {price} ¥",
            callback_data=ShopItemCallback(item=item.value))

    if not vip:
        builder.button(text="🌟", callback_data="premium_shop")

    builder.adjust(1)

    return builder.as_markup()

def premium_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 1 месяц", 
                    callback_data=VipPurchase(months=1).pack())
    builder.button(text="🗓️ 6 месяцев",
                    callback_data=VipPurchase(months=6).pack())
    builder.button(text="♾️ Навсегда", 
                    callback_data=VipPurchase(months=1200).pack())

    builder.adjust(1)
    return builder.as_markup()