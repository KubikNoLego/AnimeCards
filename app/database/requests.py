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