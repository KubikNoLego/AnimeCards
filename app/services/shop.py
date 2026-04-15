from app.database.models import User
from app.database.requests import RedisRequests
from app.utils.enums.shop import ShopEnum
from app.utils.shop import item_to_string, items_to_string


async def delete_item(user: User, item: ShopEnum) -> None:
    items = await RedisRequests().get_user_items(user)
    items_str, item_str = items_to_string(items), item_to_string(item)
    items_str = items_str.replace(item_str,"")
    await RedisRequests().update_user_items(user.id,items_str)
    return