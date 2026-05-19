from app.utils.constants import SHOP_ITEMS
from app.utils.enums.shop import ShopEnum


def items_to_string(items: list[ShopEnum]) -> str:
    chars = []
    for key, value in SHOP_ITEMS.items():
        if value in items:
            chars.append(key)
    return "".join(chars)

def item_to_string(item: ShopEnum) -> str:
    for key, value in SHOP_ITEMS.items():
        if value == item:
            return key