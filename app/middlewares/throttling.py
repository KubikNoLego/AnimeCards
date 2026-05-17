import asyncio
import math
import time
from collections import defaultdict
from typing import Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, delay: float = 5.0):
        self.delay = delay

        # время последнего сообщения
        self.last_time: Dict[int, float] = defaultdict(float)

        # защита от спама уведомлениями
        self.notification_lock: Dict[int, bool] = defaultdict(bool)

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict
    ):
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        current_time = time.time()

        elapsed = current_time - self.last_time[user_id]

        if elapsed < self.delay:
            remaining = math.ceil(self.delay - elapsed)

            if not self.notification_lock[user_id]:
                self.notification_lock[user_id] = True

                notify = await event.answer(
                    f"⏳ Подожди {remaining} сек..."
                )

                await asyncio.sleep(remaining)

                try:
                    await notify.delete()
                except:
                    pass

                self.notification_lock[user_id] = False

            return

        self.last_time[user_id] = current_time

        return await handler(event, data)