from dataclasses import dataclass

from loguru import logger

from app.database.models import User
from app.database.requests import RedisRequests, get_redis


class BuffService:

    @dataclass
    class UserBuffs:
        luck: float = 1.0
        yen: float = 1.0
        cooldown: float = 0.0

        def __repr__(self):
            return f"""<blockquote>🍀 Бонус на удачу: <b>{'-' if (self.luck-1)*100 < 0 else '+'}{abs(round(self.luck-1,3)*100)} %</b>
👝 Бонус на ¥: <b>{'-' if (self.yen-1)*100 < 0 else '+'}{abs(round(self.yen-1,3)*100)} %</b>
⌛ Бонус на время открытия: <b>{'-' if self.cooldown > 0 else '+'}{abs(round(self.cooldown))} мин.</b></blockquote>
"""

    @classmethod
    async def calculate_buffs(cls, user: User):
        
        buffs = cls.UserBuffs()

        if user.profile.title:

            title = user.profile.title

            if title.yen_boost: buffs.yen += title.yen_boost / 100
            if title.luck_boost: buffs.luck += title.luck_boost / 100
            if title.time_skip: buffs.cooldown += title.time_skip
            
        if user.vip:
            buffs.yen += .25
            buffs.luck += .1

        redis = RedisRequests(get_redis())

        if (await redis.yens_boosts(user.id)) > 0:
            buffs.yen += .20

        if (await redis.luck_boosts(user.id)) > 0:
            buffs.luck += .3

        logger.debug(f"Баффы пользователя ({user.id}): Удача {buffs.luck}\tБуст йен {buffs.yen}\tКД {buffs.cooldown}")

        return buffs