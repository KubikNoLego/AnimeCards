from aiogram import Dispatcher, Router

from app.handlers.common import promo
from app.handlers.common import (vip_callback)
from app.handlers.admin import admin
from app.handlers.common import pagination
from app.handlers.social import clan, referral, trade
from app.handlers.users import daily, open_cards, profile, shop, start, top_players

def setup_routers(dp: Dispatcher):
    """Подключает все роутеры к диспетчеру."""
    dp.include_router(clan.router)
    dp.include_router(trade.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(admin.router)
    dp.include_router(shop.router)
    dp.include_router(top_players.router)
    dp.include_router(open_cards.router)
    dp.include_router(start.router)
    dp.include_router(daily.router)
    dp.include_router(promo.router)
    dp.include_router(pagination.router)
    dp.include_router(vip_callback.router)
