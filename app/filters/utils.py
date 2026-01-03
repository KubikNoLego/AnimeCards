from aiogram.filters import BaseFilter
from aiogram.types import Message

class Private(BaseFilter):
    """Filter for private chat messages only."""

    async def __call__(self, message: Message):
        return message.chat.type == "private"

class ProfileFilter(BaseFilter):
    """Filter for profile-related messages."""

    async def __call__(self, message: Message):
        return (message.chat.type == "private" and message.text == "👤 Профиль") or message.text == ".профиль"
