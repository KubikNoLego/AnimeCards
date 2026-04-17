# Стандартные библиотеки

# Сторонние библиотеки
from aiogram.filters import BaseFilter
from aiogram.types import Message

class Private(BaseFilter):
    """Фильтр только для сообщений в приватных чатах."""

    async def __call__(self, message: Message):
        return message.chat.type == "private"

class ProfileFilter(BaseFilter):
    """Фильтр для сообщений, связанных с профилем."""

    async def __call__(self, message: Message):
        return message.chat.type == "private" and message.text == "👤 Профиль"