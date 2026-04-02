from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from db.models import Referrals, User


class ReferralRepo:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_referral(self,
            referral_id: int, referrer_id: int,
            referrer_reward: int = 0) -> Referrals | None:
        """Создаёт рефералов"""
        if referral_id != referrer_id:
            existing_referral = await self.session.scalar(
                select(Referrals).filter_by(user_id=referrer_id,
                                            referral_id=referral_id)
            )
            if not existing_referral:
                referrer = await self.session.scalar(
                    select(User).filter_by(id=referrer_id)
                )
                if referrer:
                    referral_object = Referrals(
                        user_id=referrer_id,
                        referral_id=referral_id,
                        referrer_reward=referrer_reward
                    )
                    self.session.add(referral_object)
                    await self.session.commit()
                    return referral_object
        return None

    async def get_award(self,
                        referrer_id: int, award: int) -> bool:
        """Выдаёт награду за реферала"""
        try:
            referrer = await self.session.scalar(
                select(User).filter_by(id=referrer_id)
            )
            if referrer:
                referrer.balance += award
                await self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при начислении награды за реферала: {e}")
            return False