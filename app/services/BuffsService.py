from dataclasses import dataclass

from loguru import logger

from app.database.models import User
from app.utils.constants import LUCK_BOOST, YEN_BOOST


class BuffService:

    @dataclass
    class UserBuffs:
        luck: float = 1.0
        yen: float = 1.0
        cooldown: float = 0.0

        def __repr__(self):
            return f"""<blockquote>🍀 Бонус на удачу: <b>{'-' if (self.luck-1)*100 < 0 else '+'}{abs(round((self.luck-1)*100, 2))} %</b>
👝 Бонус на ¥: <b>{'-' if (self.yen-1)*100 < 0 else '+'}{abs(round((self.yen-1)*100, 2))} %</b>
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

        if user.yen_boosts > 0:
            buffs.yen += YEN_BOOST

        if user.luck_boosts > 0:
            buffs.luck += LUCK_BOOST

        logger.debug(f"Баффы пользователя ({user.id}): Удача {buffs.luck}\tБуст йен {buffs.yen}\tКД {buffs.cooldown}")

        return buffs