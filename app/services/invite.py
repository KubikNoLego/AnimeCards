import random

from app.database.requests import DB
from app.utils.enums.invite_enums import InviteEnum


async def new_referral(db: DB, inviter_id: int, user_id: int) -> InviteEnum:
    inviter = await db.user.get_user(inviter_id)
    if not inviter:
        return InviteEnum.NOT_USER

    # Добавляем реферальную связь с указанием награды
    referral = await db.referral.add_referral(referral_id=user_id,
                                referrer_id=inviter_id,
                                referrer_reward=1 if not inviter.vip else 2)
    if not referral:
        return InviteEnum.SORRY
    
    await db.referral.get_award(inviter_id, user_id)

    return InviteEnum.SUCCESS