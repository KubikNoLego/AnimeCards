from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.enums.shop import ShopEnum

from .datas import ShopItemCallback

async def shop_keyboard_choice(card_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Купить", callback_data=f"buy_card_{card_id}")
    builder.button(text="🔙 Отмена", callback_data="cancel_buy")
    builder.adjust(2)

    return builder.as_markup()


async def shop_keyboard(items: list[ShopEnum] | list):
    """Создать инлайн-клавиатуру для магазина"""
    builder = InlineKeyboardBuilder()

    if len(items) <= 0:
        builder.button(text="Уже всё куплено", callback_data="pass")
    else:
        [builder.button(text=x.value[0], callback_data=ShopItemCallback(item=x.value[1]).pack()) for x in items]
        

    builder.adjust(2)

    return builder.as_markup()