from datetime import datetime, timedelta
from html import escape
import random

from aiogram.types import Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Banner, BannerCard, BannerPity, Card, CardType, Rarity, User, UserCards, Referrals
from app.database.requests import DB
from app.messages.MessageControl import MText
from app.services.BuffsService import BuffService
from app.utils.constants import COOLDOWN, DAILY_VERSE_BOOST, DAILY_VERSE_YEN_BOOST, MSK_TIMEZONE, SEASON_ROLL_COST, SHINY_CHANCE

class ReferralService:


    @classmethod
    def check_user_invite(cls, referral_id: int,
        referrer_id: int,
        created: bool) -> None:

        if not referral_id != referrer_id:
            raise ValueError("<b>❌ Ошибка приглашения</b>\n\n<i>Вы не можете стать своим собственным рефералом!</i>")

        if not created:
            raise ValueError("<b>❌ Ошибка приглашения</b>\n\n<i>Стать рефералом может только незарегистрированный пользователь.</i>")
        
    @classmethod
    async def add_referral(cls, referrer_id: int,
                        referral_id: int,
                        created: bool,
                        message: Message,
                        session: AsyncSession) -> None:
        
        cls.check_user_invite(referral_id, referrer_id, created)

        db = DB(session)

        referrer = await db.user.get_user(referrer_id)
        if not referrer:
            raise ValueError("<b>❌ Реферал не найден</b>\n\n<i>Пользователь с таким ID не зарегистрирован в системе.</i>\n\n<i>Проверьте правильность ссылки</i>")
        
        referral_obj = await cls.new_referral(db, referrer, referral_id)

        await cls.send_messages(message, referral_obj)
        

    @classmethod
    async def new_referral(cls, db: DB, referrer: User,
                        referral_id: int) -> None:

        referral = await db.referral.add_referral(referral_id=referral_id,
                                    referrer_id=referrer.id,
                                    reward= 150 if referrer.vip else 100)
        if not referral:
            raise ValueError("<b>❌ Ошибка регистрации</b>\n\n<i>К сожалению, мы не смогли зарегистрировать вас как реферала.</i>\n\n<i>Попробуйте позже или обратитесь в поддержку.</i>")

        return referral

    @classmethod
    async def send_messages(cls, message: Message,
                            referral_obj: Referrals) -> None:

        referrer = referral_obj.referrer
        referral = referral_obj.referral

        referrer_link = f'<a href="tg://user?id={referrer.id}">{escape(referrer.name)}</a>'
        referral_link = f'<a href="tg://user?id={referral.id}">{escape(referral.name)}</a>'
        
        await message.answer(MText.get("referral_welcome").format(referrer_link=referrer_link))

        await message.bot.send_message(
            referrer.id,
            MText.get("new_referral").format(link=referral_link,
                                            reward = referral_obj.reward)
            )
        
    @classmethod
    async def check_referral_reward(cls,
        session: AsyncSession,
        user: User) -> bool:
        """
        Проверяет, получил ли пользователь 10 карт.
        Если да — выдаёт награду рефереру.

        Возвращает True, если награда была выдана.
        """

        referral = await session.scalar(
            select(Referrals)
            .where(
                Referrals.referral_id == user.id,
                Referrals.claimed.is_(False)
            )
        )

        if referral is None:
            return False

        cards_count = await session.scalar(
            select(func.count(UserCards.id))
            .where(UserCards.user_id == user.id)
        )

        if cards_count < 10:
            return False

        referral.referrer.balance += referral.reward
        referral.claimed = True

        return True