from aiogram import Router

from . import (admin, daily, pagination, profile, promo, referral,
            shop, start, vip_callback, open_cards, top_players, trade, clan, pvp)

def setup_routers():
    router = Router()

    router.include_router(clan.router)
    router.include_router(trade.router)
    router.include_router(profile.router)
    router.include_router(pvp.router)
    router.include_router(referral.router)
    router.include_router(admin.router)
    router.include_router(shop.router)
    router.include_router(top_players.router)
    router.include_router(open_cards.router)
    router.include_router(start.router)
    router.include_router(daily.router)
    router.include_router(promo.router)
    router.include_router(pagination.router)
    router.include_router(vip_callback.router)

    return router