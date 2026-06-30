from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.models import Referrals, User


class ReferralRepo:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_referral(self,
            referral_id: int, referrer_id: int,
            reward: int = 0, claimed: bool = False) -> Referrals | None:
        """Создаёт рефералов"""
        existing_referral = await self.session.scalar(
                select(Referrals).filter_by(user_id=referrer_id,
                                            referral_id=referral_id)
            )
        if not existing_referral:
            referrer = await self.session.scalar(
                select(User).filter_by(id=referrer_id))
            if referrer:
                referral_object = Referrals(
                    user_id=referrer_id,
                    referral_id=referral_id,
                    reward=reward,
                    claimed = claimed
                    )
                
                self.session.add(referral_object)
                await self.session.commit()
                return referral_object