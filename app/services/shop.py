from app.database.models import User
from app.database.requests import RedisRequests
from app.database import get_redis
from app.utils.enums.shop import ShopEnum
from app.utils.shop import item_to_string, items_to_string


async def delete_item(user: User, item: ShopEnum) -> None:
    """Удаляет элемент из магазина пользователя."""
    redis = get_redis()
    redis_requests = RedisRequests(redis)
    items = await redis_requests.get_user_items(user)
    items_str, item_str = items_to_string(items), item_to_string(item)
    items_str = items_str.replace(item_str, "")
    await redis_requests.update_user_items(user.id, items_str)