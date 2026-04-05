from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.repositories.user_repo import UserRepo
from app.database.repositories.card_repo import CardRepo
from app.database.repositories.promo_repo import PromoRepo
from app.database.repositories.trade_repo import TradeRepo
from app.database.repositories.referral_repo import ReferralRepo
from app.database.repositories.clan_repo import ClanRepo
from app.database.repositories.pvp_repo import PVPRepo


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
        from redis.asyncio import Redis
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

    @staticmethod
    async def daily_items() -> str | None:
        """Получает элементы ежедневного магазина из Redis."""
        from redis.asyncio import Redis
        session = Redis()
        try:
            items = await session.get('shop_items') or None
            return items
        except Exception as exc:
            logger.exception(f"Ошибка при получении элементов магазина из Redis: {exc}")
            return None
        finally:
            await session.aclose()
