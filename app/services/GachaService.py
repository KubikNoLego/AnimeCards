from datetime import datetime, timedelta
import random

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Banner, BannerCard, BannerPity, Card, CardType, Rarity, User, UserCards
from app.database.requests import DB
from app.services.ReferralService import ReferralService
from app.services.BuffsService import BuffService
from app.utils.constants import COOLDOWN, DAILY_VERSE_YEN_BOOST, MSK_TIMEZONE, SEASON_ROLL_COST, SHINY_CHANCE

class GachaService:

    @classmethod
    async def add_yens(cls, user: User, card: Card, shiny: bool,
                        session: AsyncSession, is_duplicate: bool = False):
        price = card.price(shiny)
        buffs = await BuffService.calculate_buffs(user)
        daily = await DB(session).verse.get_daily_verse()

        buffs.yen += DAILY_VERSE_YEN_BOOST if daily.id == card.verse_id else 0

        # Добавляем 30% бонус за дубликаты
        if is_duplicate:
            buffs.yen += 0.3

        added = max(round(price * buffs.yen), price)

        user.balance += added

        userseason = await DB(session).season.get_user_season(user.id)
        userseason.balance += added

        await session.commit()

        logger.debug(f"Пользователь ({user.id}) получил {added} йен на баланс")

        if added > price and added-price > 0:
            return f"➕ Вы дополнительно получили <b>{added-price} ¥</b>"
        else:
            return None

    @classmethod
    def nottime(cls, last_open: datetime, buff: BuffService.UserBuffs):
        try:

            hour = COOLDOWN - (1 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 0)
            target_time = last_open + timedelta(hours=hour)
            if buff.cooldown:
                target_time -= timedelta(minutes=buff.cooldown)

            time_left = target_time - datetime.now(MSK_TIMEZONE)
            total_seconds = int(time_left.total_seconds())

            logger.debug(f"Секунд до следующего открытия: {total_seconds}")

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
        paid_rolls = max(0, amount - user.free_season_opens)
        return user.balance >= paid_rolls * SEASON_ROLL_COST

    @classmethod
    def check_able_standard(cls, user: User, buffs: BuffService.UserBuffs):

        can_roll = False

        if user.free_standard_opens > 0:
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
                            card: Card, shiny: bool) -> tuple[UserCards, bool]:

        usercard = await session.scalar(
            select(UserCards).where(
                UserCards.user_id == user.id,
                UserCards.card_id == card.id))

        used_duplicator = (
            card.card_type == CardType.SEASONAL
            and user.duplicators > 0)

        if used_duplicator:
            user.duplicators -= 1

        is_duplicate = usercard is not None

        if usercard is None:

            usercard = UserCards(
                user_id=user.id,
                card_id=card.id,
                shiny=shiny if card.card_type != CardType.SEASONAL else False,
                level=2 if used_duplicator else 1,
            )

            session.add(usercard)
            await session.flush()
            await ReferralService.check_referral_reward(session, user)

            logger.debug(f"Добавлена карта ({card.id}) пользователю ({user.id})")

            return usercard, is_duplicate

        if card.card_type == CardType.SEASONAL:

            usercard.level += 2 if used_duplicator else 1

            logger.debug(f"Добавлена карта ({card.id}) пользователю ({user.id}), уровень {usercard.level}")

            if (usercard.level >= 3
                and card.has_shiny
                and not usercard.shiny):

                usercard.shiny = True
                logger.debug(f"Карта ({card.id}) пользователя ({user.id}) стала shiny")

        else:
            if shiny and not usercard.shiny:
                usercard.shiny = True
                logger.debug(f"Карта ({card.id}) пользователя ({user.id}) стала shiny")

        return usercard, is_duplicate


    #Переделать
    @classmethod
    async def open_card(cls, user_id: int, session: AsyncSession,
                    banner_id: int) -> tuple[Card, bool]:

        user = await DB(session).user.get_user(user_id)
        buffs = await BuffService.calculate_buffs(user)

        match banner_id:

            case 1:
                now = datetime.now(MSK_TIMEZONE)
                time_since_last_open = now - user.last_open

                if now.weekday() < 5:
                    cooldown = timedelta(hours=2)
                else:
                    cooldown = timedelta(hours=3)

                if time_since_last_open >= cooldown - timedelta(minutes=buffs.cooldown):
                    user.last_open = now

                elif user.free_standard_opens > 0:
                    user.free_standard_opens -= 1

                if user.luck_boosts > 0:
                    user.luck_boosts -= 1
                if user.yen_boosts > 0:
                    user.yen_boosts -= 1

                card, shiny = await cls._roll_standard_banner(session, user, buffs)

                usercard, is_duplicate = await cls.add_card_to_user(session, user, card, shiny)

                yens_message = await cls.add_yens(user, card, shiny, session, is_duplicate)

                await session.commit()

                logger.info(f"Пользователь {user.id} получил карту {card.id}{' (Shiny)' if shiny else ''}")

                return card, shiny, yens_message

            case _:
                
                if user.free_season_opens > 0:
                    user.free_season_opens -= 1
                else:
                    user.balance -= SEASON_ROLL_COST

                card, shiny = await cls._roll_season_banner(session, user,
                                                        buffs)
                
                await cls.add_card_to_user(session, user, card, shiny)

                if user.luck_boosts > 0:
                    user.luck_boosts -= 1
                if user.yen_boosts > 0:
                    user.yen_boosts -= 1

                await session.commit()

                logger.info(f"Пользователь {user.id} получил карту {card.id}{' (Shiny)' if shiny else ''} из баннера {banner_id}")

                return card, shiny

    #Переделать
    @classmethod
    async def open_cards(cls, user_id: int, session: AsyncSession, 
                        featured_card: int,
                        amount: int = 10) -> list[tuple[Card,bool]]:
        user = await DB(session).user.get_user(user_id)

        results = []

        for _ in range(amount):

            buffs = await BuffService.calculate_buffs(user)
            if user.luck_boosts > 0:
                user.luck_boosts -= 1
            if user.yen_boosts > 0:
                user.yen_boosts -= 1
            card, shiny = await cls._roll_season_banner(session, user,
                buffs)
            
            if user.free_season_opens > 0:
                    user.free_season_opens -= 1
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
                        buffs: BuffService.UserBuffs) -> Rarity:

        banner_pity = await cls._get_pity(session, banner.id, user.id)

        if banner_pity.ssr >= 100:
            banner_pity.ssr = 0
            return await cls._force_rarity(session, 5)
        if banner_pity.sr >= 50:
            banner_pity.sr = 0
            return await cls._force_rarity(session, 4)
        if banner_pity.s >= 30:
            banner_pity.s = 0
            return await cls._force_rarity(session, 3)

        rarities = (await session.scalars(select(Rarity))).all()

        weights = []

        for rarity in rarities:
            bonus = (buffs.luck - 1) * rarity.luck_multiplier

            weight = rarity.drop_rate * (1 + bonus)

            if rarity.id == 5 and banner_pity.ssr >= 70:
                soft_bonus = 1 + ((banner_pity.ssr - 70) * 0.15)
                weight *= soft_bonus

            weights.append(weight)

        rarity = random.choices(rarities,
                                weights=weights,
                                k=1)[0]
        
        banner_pity.ssr += 1
        banner_pity.sr += 1
        banner_pity.s += 1

        if rarity.id == 5:
            banner_pity.ssr = 0
        elif rarity.id == 4:
            banner_pity.sr = 0
        elif rarity.id == 3:
            banner_pity.s = 0
        
        logger.debug(f"Получена редкость {rarity.name} ({rarity.id}) для пользователя ({user.id})")

        return rarity
    
    @classmethod
    async def _roll_standard_banner(cls, session: AsyncSession, user: User,
                            buffs: BuffService.UserBuffs) -> tuple[Card, bool]:
        
        banner = await session.scalar(select(Banner).where(Banner.id == 1))

        rarity = await cls._roll_rarity(session, user, banner,buffs)


        cards = (await session.scalars(select(Card)
                        .where(Card.rarity_id == rarity.id,
                                Card.card_type == CardType.STANDARD,
                                Card.verse_id == Banner.verse_id,
                                Card.droppable == True))).all()

        if not cards:
            raise ValueError(f"Нет карт для редкости {rarity.name}")

        card = random.choice(cards)

        shiny = False

        if card.has_shiny:
            
            if random.random() <= SHINY_CHANCE:
                shiny = True

        return card, shiny

    #Переделать
    @classmethod
    async def _roll_season_banner(cls, session: AsyncSession, user: User,
                    buffs: BuffService.UserBuffs) -> tuple[Card, bool]:
        
        season = await DB(session).season.get_active_season()
        banner = season.banner

        rarity = await cls._roll_rarity(session, user, banner, buffs)
        
        
        if banner.verse_id:
            cards = (await session.scalars(select(Card).where(
                        Card.droppable == True,
                        Card.card_type == CardType.STANDARD,
                        Card.verse_id == banner.verse_id,
                        Card.rarity_id == rarity.id))).all()
        else:
            cards = []

        if not cards:
            cards = (await session.scalars(select(Card).where(
                        Card.droppable == True,
                        Card.card_type == CardType.STANDARD,
                        Card.rarity_id == rarity.id))).all()

        banner_cards = (
            await session.scalars(select(Card).join(BannerCard).where(
                BannerCard.banner_id == banner.id,
                Card.rarity_id == rarity.id,
                Card.droppable == True))).all()
        cards.extend(banner_cards)


        if not cards:
            raise ValueError(f"Нет карт для редкости {rarity.name}")
        
        weights = []

        for card in cards:
            
            weight = 1.0
            
            if card.card_type == CardType.SEASONAL:
                weight *= 20

            weights.append(weight)

        card = random.choices(cards, weights, k=1)[0]

        shiny = False

        if card.has_shiny and card.card_type != CardType.SEASONAL:
            
            if random.random() <= SHINY_CHANCE:
                shiny = True

        return card, shiny