from aiogram import Router

from .messages import (clan, profile, referral, shop, top_players, open_cards,
                    admin, trade)
from .commands import (start, open_card_command, profile_command,daily,
                    top_players_command, admin_command,promo,clan_command)
from .callbacks import (clan_callback, shop_callback,pagination,
                        admin_callbacks, vip_callback, trade_callback)

def setup_routers():
    router = Router()

    router.include_router(clan.router)
    router.include_router(trade.router)
    router.include_router(profile.router)
    router.include_router(referral.router)
    router.include_router(admin.router)
    router.include_router(shop.router)
    router.include_router(top_players.router)
    router.include_router(open_cards.router)
    router.include_router(start.router)
    router.include_router(open_card_command.router)
    router.include_router(profile_command.router)
    router.include_router(daily.router)
    router.include_router(clan_command.router)
    router.include_router(top_players_command.router)
    router.include_router(promo.router)
    router.include_router(admin_command.router)
    router.include_router(clan_callback.router)
    router.include_router(shop_callback.router)
    router.include_router(pagination.router)
    router.include_router(admin_callbacks.router)
    router.include_router(vip_callback.router)
    router.include_router(trade_callback.router)

    return router
