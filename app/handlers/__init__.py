from aiogram import Router

from . import start,messages,callbacks

def setup_routers():
    router = Router()
    router.include_router(start.router)
    router.include_router(messages.router)
    router.include_router(callbacks.router)
    return router
