from dataclasses import dataclass
from datetime import datetime, timedelta
import random

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Banner, BannerCard, BannerPity, Card, CardType, Rarity, User, UserCards
from app.database.requests import DB, RedisRequests, get_redis
from app.utils.constants import COOLDOWN, DAILY_VERSE_BOOST, DAILY_VERSE_YEN_BOOST, MSK_TIMEZONE, SEASON_ROLL_COST, SHINY_CHANCE


class LuckService:

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

class GachaService:

    @classmethod
    async def add_yens(cls, user: User, card: Card, shiny: bool, 
                        session: AsyncSession):
        price = card.price(shiny)
        buffs = await LuckService.calculate_buffs(user)
        daily = await DB(session).card.get_daily_verse()
        
        buffs.yen += DAILY_VERSE_YEN_BOOST if daily.id == card.verse_id else 0

        added = max(round(price * buffs.yen), price)

        user.balance += added
        await session.commit()

        logger.debug(f"Пользователь ({user.id}) получил {added} йен")

        if added > price and added-price > 0:
            return f"➕ Вы дополнительно получили <b>{added-price} ¥</b>"
        else:
            return None

    @classmethod
    def nottime(cls, last_open: datetime, buff: LuckService.UserBuffs):
        try:

            hour = COOLDOWN - (1 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 0)
            target_time = last_open + timedelta(hours=hour)
            if buff.cooldown:
                target_time -= timedelta(minutes=buff.cooldown)

            time_left = target_time - datetime.now(MSK_TIMEZONE)
            total_seconds = int(time_left.total_seconds())

            logger.debug(f"Секунд до следущего открытия: {total_seconds}")

            if total_seconds < 0:
                formatted_time = "00:00"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                formatted_time = f"{hours:02d}:{minutes:02d}"

            return "<b>⏳ Подождите</b>\n\n<i>До следующего открытия осталось <b>{time}</b></i>\n\n<i>Попробуйте открыть карту позже.</i>".format(time=formatted_time)
        except Exception as e:
            logger.exception(f"Ошибка форматирования времени: {e}")
            return "<i>⏳ До следующего открытия осталось немного времени</i>"

    @classmethod
    def check_able_season(cls, user: User, amount: int = 1):
        paid_rolls = max(0, amount - user.free_open)
        return user.balance >= paid_rolls * SEASON_ROLL_COST

    @classmethod
    def check_able_standard(cls, user: User, buffs: LuckService.UserBuffs):

        can_roll = False

        if user.free_open > 0:
            can_roll = True
        else:
            now = datetime.now(MSK_TIMEZONE)
            time_since_last_open = now - user.last_open

            if now.weekday() < 5:
                cooldown = timedelta(hours=2)
            else:
                cooldown = timedelta(hours=3)

            if time_since_last_open >= cooldown - timedelta(
                                                    minutes=buffs.cooldown):
                can_roll = True

        return can_roll

    @classmethod
    async def add_card_to_user(cls, session: AsyncSession, user: User,
                            card: Card, shiny: bool) -> UserCards:

        usercard = await session.scalar(select(UserCards).where(
            UserCards.user_id == user.id,
            UserCards.card_id == card.id))
        
        
        if usercard is None:

            usercard = UserCards(user_id = user.id, card_id = card.id,
                                shiny=shiny 
                                if card.card_type != CardType.SEASONAL 
                                else False)
            
            session.add(usercard)
            await session.flush()
            logger.debug(f"Добавлена карта ({card.id}) пользователю ({user.id})")

            return usercard

        if card.card_type == CardType.SEASONAL:
            
            usercard.level += 1
            logger.debug(f"Добавлена карта ({card.id}) пользователю ({user.id} уровень {usercard.level})")
            
            if (usercard.level >= 3 and 
            card.has_shiny and 
            usercard.shiny == False):

                usercard.shiny = True
                logger.debug(f"Карта ({card.id}) пользователя ({user.id}) стала shiny")

        else:
            if shiny and not usercard.shiny:
                usercard.shiny = True
                logger.debug(f"Карта ({card.id}) пользователя ({user.id}) стала shiny")

        return usercard


    @classmethod
    async def open_card(cls, user_id: int, session: AsyncSession,
                    banner_id: int, featured_card: int | None) -> tuple[Card, bool]:

        user = await DB(session).user.get_user(user_id)

        match banner_id:

            case 1:
                buffs = await LuckService.calculate_buffs(user)
                card, shiny = await cls._roll_standard_banner(session, user, buffs)

                await cls.add_card_to_user(session, user, card, shiny)

                if user.free_open > 0:
                    user.free_open -= 1
                else:
                    user.last_open = datetime.now(MSK_TIMEZONE)

                await session.commit()

                logger.info(f"Пользователь {user.id} получил карту {card.id}{' (Shiny)' if shiny else ''}")

                return card,shiny

            case _:
                buffs = await LuckService.calculate_buffs(user)
                
                if user.free_open > 0:
                    user.free_open -= 1
                else:
                    user.balance -= SEASON_ROLL_COST

                card, shiny = await cls._roll_season_banner(session, user,
                                                        buffs, featured_card)
                
                await cls.add_card_to_user(session, user, card, shiny)

                await session.commit()

                logger.info(f"Пользователь {user.id} получил карту {card.id}{' (Shiny)' if shiny else ''} из баннера {banner_id}")

                return card, shiny

    @classmethod
    async def open_cards(cls, user_id: int, session: AsyncSession, 
                        featured_card: int,
                        amount: int = 10) -> list[tuple[Card,bool]]:
        user = await DB(session).user.get_user(user_id)

        results = []

        buffs = await LuckService.calculate_buffs(user)

        for _ in range(amount):
            card, shiny = await cls._roll_season_banner(session, user,
                buffs, featured_card)
            
            if user.free_open > 0:
                    user.free_open -= 1
            else:
                user.balance -= SEASON_ROLL_COST
            
            await cls.add_card_to_user(session, user, card, shiny)

            results.append((card, shiny))

        await session.commit()

        return results


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

            pity = BannerPity(banner_id=banner_id, user_id=user_id)
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
        if banner_pity.s_pity >= 30:
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
        
        logger.debug(f"Получена редкость {rarity.name} ({rarity.id}) для пользователя ({user.id})")

        return rarity
    
    @classmethod
    async def _roll_standard_banner(cls, session: AsyncSession, user: User,
                            buffs: LuckService.UserBuffs) -> tuple[Card, bool]:
        
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

    @classmethod
    async def _roll_season_banner(cls, session: AsyncSession, user: User,
                    buffs: LuckService.UserBuffs, featured_card: int) -> tuple[Card, bool]:
        banner = await session.scalar(select(Banner).where(
                                    Banner.active == True, Banner.id != 1))
        
        rarity = await cls._roll_rarity(session, user, banner, buffs)
        
        
        cards = (await session.scalars(select(Card).where(
                    Card.droppable == True,
                    Card.card_type == CardType.STANDARD,
                    Card.rarity_id == rarity.id))).all()
        
        if rarity.id != 5:
            banner_cards = (
                await session.scalars(select(Card).join(BannerCard).where(
                    BannerCard.banner_id == banner.id, 
                    Card.rarity_id == rarity.id,
                    Card.droppable == True))).all()
            cards.extend(banner_cards)

        else: 
            featured_card = await session.scalar(select(Card)
                                            .where(Card.id == featured_card))
            cards.append(featured_card)

        if not cards:
            raise ValueError(f"Нет карт для редкости {rarity.name}")
        
        weights = []

        for card in cards:
            
            weight = 1.0

            if card.verse_id == banner.verse_id:
                weight *= 5
            
            if card.card_type == CardType.SEASONAL:
                weight *= 40

            weights.append(weight)

        card = random.choices(cards, weights, k=1)[0]

        shiny = False

        if card.has_shiny and card.card_type != CardType.SEASONAL:
            
            if random.random() <= SHINY_CHANCE:
                shiny = True

        return card, shiny