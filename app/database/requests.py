from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from redis.asyncio import Redis

from app.database.models import User
from app.database.repositories.user_repo import UserRepo
from app.database.repositories.card_repo import CardRepo
from app.database.repositories.promo_repo import PromoRepo
from app.database.repositories.trade_repo import TradeRepo
from app.database.repositories.referral_repo import ReferralRepo
from app.database.repositories.clan_repo import ClanRepo
from app.database.repositories.pvp_repo import PVPRepo
from app.utils.consts import SHOP_ITEMS
from app.utils.enums.shop import ShopEnum

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
    """Класс для работы с Redis."""

    @staticmethod
    async def daily_verse() -> int | None:
        """Получает ежедневную вселенную из Redis."""
        session = None
        try:
            session = Redis()
            verse = await session.get('daily_verse')
            if verse:
                return int(verse.decode('utf-8'))
            return None
        except Exception as exc:
            logger.exception(f"Ошибка при получении ежедневной вселенной из Redis: {exc}")
            return None
        finally:
            if session:
                await session.aclose()

    async def create_user_items(self,user: User) -> None:
        session = None
        try:
            session = Redis()
            await session.set(f'shop:{user.id}',"fbay" if not user.vip else "fbayr",
                    ex=24*60*60)
        except Exception as e:    
            logger.exception(f"get_user_items: {e}")
            return []

    async def get_user_items(self,user: User) -> list[ShopEnum]:
        session = None
        shop_items = []
        try:
            session = Redis()
            
            if await session.exists(f'shop:{user.id}'):
                shop_items_keys = await session.get(f'shop:{user.id}')
                for key in shop_items_keys.decode():
                    shop_items.append(SHOP_ITEMS.get(key))
            else:

                await self.create_user_items(user)

                shop_items = (list(SHOP_ITEMS.values())[:-1] + 
                            [SHOP_ITEMS.get('r')] if user.vip else [])
            
            return shop_items

        except Exception as e:
            logger.exception(f"get_user_items: {e}")
            return []

    async def update_user_items(self, user_id: int, items: str) -> None:
        session = None
        try:
            session = Redis()
            await session.set(f'shop:{user_id}', items, keepttl=True)
        except Exception as e:
            logger.exception(f"update user items: {e}")

    async def luck_boosts(self, user_id: int) -> int:
        session = None
        try:
            session = Redis()
            if await session.exists(f"luck:{user_id}"):
                boosts = await session.get(f'luck:{user_id}')
                return int(boosts.decode())
            return 0
        except Exception as e:
            logger.exception(f"luck boosts: {e}")
    
    async def add_luck_boost(self,user_id: int) -> None:
        session = None
        try:
            session = Redis()
            boosts = await self.luck_boosts(user_id)
            if boosts > 0: 
                await session.set(f"luck:{user_id}", boosts+1,ex=3*24*60*60)
            else:
                await session.set(f"luck:{user_id}", 1, ex=3*24*60*60)
        except Exception as e:
            logger.exception(f"add luck boost: {e}")

    async def remove_luck_boost(self,user_id: int) -> None:
        session = None
        try:
            session = Redis()
            boosts = await self.luck_boosts(user_id)
            if boosts > 1:
                await session.set(f"luck:{user_id}", boosts-1,ex=3*24*60*60)
            else:
                await session.delete(f"luck:{user_id}")
        except Exception as e:
            logger.exception(f"remove luck boost: {e}")

    async def yens_boosts(self, user_id: int) -> int:
        session = None
        try:
            session = Redis()
            if await session.exists(f"yens:{user_id}"):
                boosts = await session.get(f'yens:{user_id}')
                return int(boosts.decode())
            return 0
        except Exception as e:
            logger.exception(f"yens boosts: {e}")
    
    async def add_yens_boost(self,user_id: int) -> None:
        session = None
        try:
            session = Redis()
            boosts = await self.yens_boosts(user_id)
            if boosts > 0: 
                await session.set(f"yens:{user_id}", boosts+1,ex=3*24*60*60)
            else:
                await session.set(f"yens:{user_id}", 1, ex=3*24*60*60)
        except Exception as e:
            logger.exception(f"add yens boost: {e}")

    async def remove_yens_boost(self,user_id: int) -> None:
        session = None
        try:
            session = Redis()
            boosts = await self.yens_boosts(user_id)
            if boosts > 1:
                await session.set(f"yens:{user_id}", boosts-1,ex=3*24*60*60)
            else:
                await session.delete(f"yens:{user_id}")
        except Exception as e:
            logger.exception(f"remove yens boost: {e}")
