from aiogram import Router

from . import commands,messages,callbacks

def setup_routers():
    router = Router()
    router.include_router(commands.router)
    router.include_router(messages.router)
    router.include_router(callbacks.router)
    return router
