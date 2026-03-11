from aiogram.utils.keyboard import InlineKeyboardBuilder

from .CallbackDatas import ShopItemCallback

async def shop_keyboard_choice(card_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Купить", callback_data=f"buy_card_{card_id}")
    builder.button(text="🔙 Отмена", callback_data="cancel_buy")
    builder.adjust(2)

    return builder.as_markup()


async def shop_keyboard(cards: list):
    """Создать инлайн-клавиатуру для магазина"""
    builder = InlineKeyboardBuilder()

    [builder.button(text=f"{card.name} ({int(card.value)} ¥)",
                callback_data=ShopItemCallback(item_id=card.id).pack(),
                style = "primary") for card in cards]
        

    builder.adjust(2)

    return builder.as_markup()