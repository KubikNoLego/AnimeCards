from dataclasses import dataclass
from datetime import datetime, timedelta
import random

from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from aiogram.types import Message, CallbackQuery

from app.database.models import Banner, BannerPity, Card, CardType, Rarity, User, UserCards
from app.database.requests import DB, RedisRequests, get_redis
from app.utils.constants import COOLDOWN, DAILY_VERSE_BOOST, MSK_TIMEZONE, SHINY_CHANCE
from app.utils.enums.banner import BannerType
from app.utils.enums.open_card_enums import CardOpen


class LuckService:

    @dataclass
    class UserBuffs:
        luck: float = 1.0
        yen: float = 1.0
        cooldown: float = 1.0

    @classmethod
    async def calculate_buffs(cls, user: User):
        
        buffs = cls.UserBuffs()

        if user.profile.title:

            title = user.profile.title

            if title.yen_boost: buffs.yen += title.yen_boost / 100
            if title.luck_boost: buffs.luck += title.luck_boost / 100
            if title.time_skip: buffs.cooldown -= title.time_skip
            
        if user.vip:
            buffs.yen += .25
            buffs.luck += .1

        redis = RedisRequests(get_redis())

        if (await redis.yens_boosts(user.id)) > 0:
            buffs.yen += .20

        if (await redis.luck_boosts(user.id)) > 0:
            buffs.luck += .1


        return buffs

class GachaService:

    @classmethod
    async def add_card_to_user(cls, session: AsyncSession, user: User,
                            card: Card, shiny: bool) -> UserCards:
        
        usercard = await session.scalar(select(UserCards).where(
            UserCards.user_id == user.id,
            UserCards.card_id == card.id
        ))

        if usercard is None:

            usercard = UserCards(user_id = user.id, card_id = card.id,
                                shiny=shiny)
            
            session.add(usercard)

            await session.flush()

            return usercard
        
        if shiny and not usercard.shiny:
            usercard.shiny = True

        return usercard


    @classmethod
    async def open_card(cls, message: Message, session: AsyncSession, banner_id: int):
        
        user = await DB(session).user.get_user(message.from_user.id)

        match banner_id:
            
            case 1:
                buffs = await LuckService.calculate_buffs(user)
                card, shiny = await cls._roll_standart_banner(session, user, buffs)

                await cls.add_card_to_user(session, user, card, shiny)

                await session.commit()

                logger.info(f"Пользователь {user.id} получил карту {card.id}{' (Shiny)' if shiny else ''}")

                return card,shiny


    @classmethod
    async def _force_rarity(cls, session: AsyncSession,
                            rarity_id: int) -> Rarity:
        rarity = await session.scalar(select(Rarity).where(Rarity.id == rarity_id))

        return rarity

    @classmethod
    async def _get_pity(cls, session: AsyncSession, 
                        banner_id: int, user_id: int) -> BannerPity:
        pity = await session.scalar(select(BannerPity)
                            .where(BannerPity.banner_id == banner_id,
                                BannerPity.user_id == user_id))
        
        if pity is None:

            pity = BannerPity(banner_id=banner_id, user_id=user_id, pity=0)
            session.add(pity)
            await session.flush()

        return pity

    @classmethod
    async def _roll_rarity(cls, session: AsyncSession, 
                        user: User, banner: Banner,
                        buffs: LuckService.UserBuffs) -> Rarity:

        banner_pity = await cls._get_pity(session, banner.id, user.id)

        if banner_pity.ssr_pity >= 100:
            banner_pity.ssr_pity = 0
            return await cls._force_rarity(session, 5)
        if banner_pity.sr_pity >= 50:
            banner_pity.sr_pity = 0
            return await cls._force_rarity(session, 4)
        if banner_pity.s_pity >= 20:
            banner_pity.s_pity = 0
            return await cls._force_rarity(session, 3)

        rarities = (await session.scalars(select(Rarity))).all()

        weights = []

        for rarity in rarities:
            bonus = (buffs.luck - 1) * rarity.luck_multiplier

            weight = rarity.drop_rate * (1 + bonus)

            if rarity.id == 5 and banner_pity.ssr_pity >= 70:
                soft_bonus = 1 + ((banner_pity.ssr_pity - 70) * 0.15)
                weight *= soft_bonus

            weights.append(weight)

        rarity = random.choices(rarities,
                                weights=weights,
                                k=1)[0]
        
        banner_pity.ssr_pity += 1
        banner_pity.sr_pity += 1
        banner_pity.s_pity += 1

        if rarity.id == 5:
            banner_pity.ssr_pity = 0
        elif rarity.id == 4:
            banner_pity.sr_pity = 0
        elif rarity.id == 3:
            banner_pity.s_pity = 0
            
        return rarity
    
    @classmethod
    async def _roll_standart_banner(cls, session: AsyncSession, user: User, buffs: LuckService.UserBuffs) -> tuple[Card, bool]:
        
        banner = await session.scalar(select(Banner).where(Banner.id == 1))

        rarity = await cls._roll_rarity(session, user, banner,buffs)


        cards = (await session.scalars(select(Card)
                        .where(Card.rarity_id == rarity.id,
                                Card.card_type == CardType.STANDARD,
                                Card.droppable == True))).all()

        if not cards:
            raise ValueError(f"Нет карт для редкости {rarity.name}")

        boosted_daily_verse = await DB(session).card.get_daily_verse()

        weights = []

        for card in cards:
            
            weight = 1.0

            if card.verse_id == boosted_daily_verse.id:

                weight *= DAILY_VERSE_BOOST
            
            weights.append(weight)

        card = random.choices(cards, weights, k=1)[0]

        shiny = False

        if card.has_shiny:
            
            if random.random() <= SHINY_CHANCE:
                shiny = True

        return card, shiny
