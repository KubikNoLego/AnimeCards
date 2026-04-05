# Модели SQLAlchemy (без циклических зависимостей)
from .models import (
    Base, User, Card, Profile, Verse, Rarity, Referrals, Clan,
    ClanMember, VipSubscription, UserCards, ClanInvitation,
    Promo, PromoUsers, Trade, BattleInventory, PvPSearchQueue
)

# Сессии и движок
from .session import create_engine, create_sessionmaker

# Репозитории (могут импортироваться напрямую)
from .repositories.user_repo import UserRepo
from .repositories.card_repo import CardRepo
from .repositories.promo_repo import PromoRepo
from .repositories.trade_repo import TradeRepo
from .repositories.referral_repo import ReferralRepo
from .repositories.clan_repo import ClanRepo

# Requests (DB и RedisRequests) - импортируются в конце, чтобы избежать циклических зависимостей
# DB использует репозитории, поэтому должен импортироваться после них
from .requests import DB, RedisRequests

__all__ = [
    # Models
    "Base", "User", "Card", "Profile", "Verse", "Rarity", "Referrals",
    "Clan", "ClanMember", "VipSubscription", "UserCards", "ClanInvitation",
    "Promo", "PromoUsers", "Trade", "BattleInventory", "PvPSearchQueue",
    # Session
    "create_engine", "create_sessionmaker",
    # Repositories
    "UserRepo", "CardRepo", "PromoRepo", "TradeRepo", "ReferralRepo", "ClanRepo",
    # Requests
    "DB", "RedisRequests",
]
