from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import Config


def create_bot(config: Config) -> Bot:
    return Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )


def create_dispatcher(config: Config) -> Dispatcher:
    return Dispatcher(storage=RedisStorage.from_url(
    config.REDIS_URL.get_secret_value(), 
    state_ttl=timedelta(days=3),
    data_ttl=timedelta(days=1))
    )