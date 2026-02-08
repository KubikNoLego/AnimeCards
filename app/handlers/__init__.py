from aiogram import Router

from . import commands,messages,callbacks,vip,admin

def setup_routers():
    router = Router()
    router.include_router(commands.router)
    router.include_router(messages.router)
    router.include_router(callbacks.router)
    router.include_router(vip.router)
    router.include_router(admin.router)
    return router
