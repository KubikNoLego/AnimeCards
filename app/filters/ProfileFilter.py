from aiogram.filters import BaseFilter
from aiogram.types import Message

class ProfileFilter(BaseFilter):

    async def __call__(self, message:Message):
        return (message.chat.type == "private" and message.text=="👤 Профиль") or message.text==".профиль"