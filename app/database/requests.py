from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from redis.asyncio import Redis
from typing import Optional

from app.database.models import User
from app.database.repositories.user_repo import UserRepo
from app.database.repositories.card_repo import CardRepo
from app.database.repositories.promo_repo import PromoRepo
from app.database.repositories.trade_repo import TradeRepo
from app.database.repositories.referral_repo import ReferralRepo
from app.database.repositories.clan_repo import ClanRepo
from app.database.repositories.pvp_repo import PVPRepo
from app.utils.constants import SHOP_ITEMS, DAILY_VERSE_TTL, BOOST_TTL
from app.utils.enums.shop import ShopEnum



# Глобальный экземпляр Redis для использования в статических методах
_redis_instance: Optional[Redis] = None


def get_redis(redis_url: str = None) -> Redis:
    """
    Получает или создает глобальный экземпляр Redis подключения.
    
    Args:
        redis_url: URL для подключения к Redis (опционально, если уже инициализирован)
        
    Returns:
        Экземпляр Redis подключения
    """
    global _redis_instance
    if _redis_instance is None:
        if redis_url is None:
            from app.config import config
            redis_url = config.REDIS_URL.get_secret_value()
        _redis_instance = Redis.from_url(redis_url)
    return _redis_instance


async def close_redis() -> None:
    """Закрывает глобальное подключение к Redis."""
    global _redis_instance
    if _redis_instance:
        await _redis_instance.aclose()
        _redis_instance = None


class DB:
    """Фасад для доступа ко всем репозиториям базы данных."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user = UserRepo(session)
        self.card = CardRepo(session)
        self.promo = PromoRepo(session)
        self.trade = TradeRepo(session)
        self.referral = ReferralRepo(session)
        self.clan = ClanRepo(session)
        self.pvp = PVPRepo(session)


class RedisRequests:
    """Класс для работы с Redis с использованием Dependency Injection."""

    def __init__(self, redis: Redis):
        """
        Инициализация с готовым подключением к Redis.
        
        Args:
            redis: Экземпляр подключения к Redis
        """
        self._redis = redis

    async def _get_redis(self) -> Redis:
        """Возвращает подключение к Redis."""
        return self._redis

    async def create_user_items(self, user: User) -> None:
        """
        Создает начальные items пользователя в Redis.
        Для VIP пользователей добавляет дополнительный item.
        
        Args:
            user: Объект пользователя
        """
        try:
            redis = await self._get_redis()
            initial_value = "fbay"
            await redis.set(f'shop:{user.id}', initial_value, ex=DAILY_VERSE_TTL)
            logger.debug(f"Созданы начальные items для пользователя {user.id}: {initial_value}")
        except Exception as e:
            logger.error(f"Ошибка при создании items для пользователя {user.id}: {e}")

    async def get_user_items(self, user: User) -> list[ShopEnum]:
        """
        Получает items пользователя из Redis.
        Если ключ не существует, создает его с начальными значениями.
        
        Args:
            user: Объект пользователя
            
        Returns:
            Список элементов магазина
        """
        try:
            redis = await self._get_redis()
            
            if await redis.exists(f'shop:{user.id}'):
                shop_items = []
                shop_items_keys = await redis.get(f'shop:{user.id}')
                if shop_items_keys:
                    for key in shop_items_keys.decode():
                        item = SHOP_ITEMS.get(key)
                        if item:
                            shop_items.append(item)
                return shop_items
            else:
                # Создаем новые items для пользователя
                await self.create_user_items(user)
                shop_items = (list(SHOP_ITEMS.values())[:-1] +
                            [SHOP_ITEMS.get('r')] if user.vip else [])
                logger.debug(f"Созданы новые items для пользователя {user.id}")
                return shop_items

        except Exception as e:
            logger.error(f"Ошибка при получении items пользователя {user.id}: {e}")
            return []

    async def update_user_items(self, user_id: int, items: str) -> None:
        """
        Обновляет items пользователя в Redis, сохраняя TTL.
        
        Args:
            user_id: ID пользователя
            items: Строка с элементами
        """
        try:
            redis = await self._get_redis()
            await redis.set(f'shop:{user_id}', items, keepttl=True)
            logger.debug(f"Обновлены items для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении items для пользователя {user_id}: {e}")

    async def luck_boosts(self, user_id: int) -> int:
        """
        Получает количество boost'ов удачи для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество boost'ов (0 если не существует)
        """
        try:
            redis = await self._get_redis()
            if await redis.exists(f"luck:{user_id}"):
                boosts = await redis.get(f'luck:{user_id}')
                return int(boosts.decode())
            return 0
        except Exception as e:
            logger.error(f"Ошибка при получении boost'ов удачи для пользователя {user_id}: {e}")
            return 0

    async def add_luck_boost(self, user_id: int) -> None:
        """
        Добавляет boost удачи для пользователя.
        Увеличивает счетчик на 1 или устанавливает 1, если не существует.
        
        Args:
            user_id: ID пользователя
        """
        try:
            redis = await self._get_redis()
            boosts = await self.luck_boosts(user_id)
            new_boosts = boosts + 1 if boosts > 0 else 1
            await redis.set(f"luck:{user_id}", new_boosts, ex=BOOST_TTL)
            logger.debug(f"Добавлен boost удачи для пользователя {user_id}: {new_boosts}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении boost'а удачи для пользователя {user_id}: {e}")

    async def remove_luck_boost(self, user_id: int) -> None:
        """
        Удаляет один boost удачи для пользователя.
        Если счетчик становится 0, ключ удаляется.
        
        Args:
            user_id: ID пользователя
        """
        try:
            redis = await self._get_redis()
            boosts = await self.luck_boosts(user_id)
            if boosts > 1:
                await redis.set(f"luck:{user_id}", boosts - 1, ex=BOOST_TTL)
                logger.debug(f"Удален boost удачи для пользователя {user_id}: {boosts - 1}")
            else:
                await redis.delete(f"luck:{user_id}")
                logger.debug(f"Удален последний boost удачи для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при удалении boost'а удачи для пользователя {user_id}: {e}")

    async def yens_boosts(self, user_id: int) -> int:
        """
        Получает количество boost'ов йен для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество boost'ов (0 если не существует)
        """
        try:
            redis = await self._get_redis()
            if await redis.exists(f"yens:{user_id}"):
                boosts = await redis.get(f'yens:{user_id}')
                return int(boosts.decode())
            return 0
        except Exception as e:
            logger.error(f"Ошибка при получении boost'ов йен для пользователя {user_id}: {e}")
            return 0

    async def add_yens_boost(self, user_id: int) -> None:
        """
        Добавляет boost йен для пользователя.
        Увеличивает счетчик на 1 или устанавливает 1, если не существует.
        
        Args:
            user_id: ID пользователя
        """
        try:
            redis = await self._get_redis()
            boosts = await self.yens_boosts(user_id)
            new_boosts = boosts + 1 if boosts > 0 else 1
            await redis.set(f"yens:{user_id}", new_boosts, ex=BOOST_TTL)
            logger.debug(f"Добавлен boost йен для пользователя {user_id}: {new_boosts}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении boost'а йен для пользователя {user_id}: {e}")

    async def remove_yens_boost(self, user_id: int) -> None:
        """
        Удаляет один boost йен для пользователя.
        Если счетчик становится 0, ключ удаляется.
        
        Args:
            user_id: ID пользователя
        """
        try:
            redis = await self._get_redis()
            boosts = await self.yens_boosts(user_id)
            if boosts > 1:
                await redis.set(f"yens:{user_id}", boosts - 1, ex=BOOST_TTL)
                logger.debug(f"Удален boost йен для пользователя {user_id}: {boosts - 1}")
            else:
                await redis.delete(f"yens:{user_id}")
                logger.debug(f"Удален последний boost йен для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при удалении boost'а йен для пользователя {user_id}: {e}")
