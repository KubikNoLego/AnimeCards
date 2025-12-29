from aiogram import Router

from . import start,messages

def setup_routers():
    router = Router()
    router.include_router(start.router)
    router.include_router(messages.router)
    return router