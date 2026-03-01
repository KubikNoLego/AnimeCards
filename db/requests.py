import random
from datetime import datetime, timedelta, timedelta
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (Card, Clan, ClanMember, Promo,
                        User, Profile, UserCards, Verse, Referrals,
                        ClanInvitation,Trade)

class DB:
    def __init__(self, session):
        self.__session: AsyncSession = session

    async def get_clan(self,clan_id: int) -> Clan | None:
        """Получает пользователя из БД, если он есть"""
        try:
            return await self.__session.scalar(select(Clan)
                                            .filter_by(id=clan_id))
        except Exception as exc:
            logger.exception(
                f"Ошибка при получении пользователя id={clan_id}: {exc}")
            return None

    async def get_user(self,user_id: int) -> User | None:
        """Получает пользователя из БД, если он есть"""
        try:
            return await self.__session.scalar(select(User)
                                            .filter_by(id=user_id))
        except Exception as exc:
            logger.exception(
                f"Ошибка при получении пользователя id={user_id}: {exc}")
            return None

    async def create_or_update_user(self, id: int,
                                    username: str | None,
                                    name: str,
                                    describe: str):
        """Создаёт пользователя, если нет, иначе обновляет поля."""
        from app.func import MSK_TIMEZONE
        now = datetime.now(MSK_TIMEZONE)
        try:
            user = await self.get_user(id)
            if user is None:
                user = User(
                    id=id,
                    username=username,
                    name=name,
                    last_open=now - timedelta(hours=3),
                )
                user.profile = Profile(user_id=id, describe=describe, joined=now)
                self.__session.add(user)
                action = True
            else:
                user.username = username
                user.name = name
                action = False
            await self.__session.commit()
            return (user, action) # возвращает пользователя и True если он создан, False - обновлён
        except Exception as exc:
            logger.exception(f"Ошибка при сохранении пользователя id={id}: {exc}")
            return None

    async def get_user_place_on_top(self,user: User):
        """Возвращает место пользователя в топе по `yens` (1 — наилучшее)."""
        stmt = select(func.count(User.id)).where(User.balance > user.balance)
        result = await self.__session.execute(stmt)
        count_higher = result.scalar()

        place = (count_higher or 0) + 1
        return place


    async def get_top_players_by_balance(self,
                                        limit: int = 10) -> list[User]:
        """Возвращает топ юзеров по балансу"""
        try:
            stmt = select(User).order_by(User.balance.desc()).limit(limit)
            result = await self.__session.execute(stmt)
            top_players = result.scalars().all()
            return top_players
        except Exception as exc:
            logger.exception(f"Ошибка при получении топ игроков по балансу: {exc}")
            return []


    async def get_random_verse(self) -> Verse:
        """Возвращает случайную вселенную, в которой есть хотя бы одна карта, которая может выпадать"""
        try:
            valid_verse_names_subquery = (
                select(Card.verse_name)
                .where(Card.can_drop == True)
                .distinct()
            )
            
            verses = await self.__session.scalars(
                select(Verse).where(Verse.name.in_(valid_verse_names_subquery))
            )
            verses = verses.all()

            if not verses:
                logger.warning("Нет доступных вселенных в базе данных")
                return None

            return random.choice(verses)
        except Exception as exc:
            logger.exception(f"Ошибка при получении случайной вселенной: {exc}")
            return None

    async def get_verse(self, verse_id: int) -> Verse | None:
        """Возвращает вселенную по ID"""
        try:
            return await self.__session.scalar(select(Verse).filter_by(id=verse_id))
        except Exception as exc:
            logger.exception(f"Ошибка при получении вселенной id={verse_id}: {exc}")
            return None

    async def get_daily_shop_items(self) -> list[Card]:
        """Возвращает карточки для магазина"""
        try:
            # Локальный импорт для избежания циклических зависимостей
            from app.func import random_card

            daily_cards = []
            attempts = 0
            max_attempts = 100

            while len(daily_cards) < 4 and attempts < max_attempts:
                attempts += 1
                try:
                    card = await random_card(self.__session, pity=100)

                    # Проверяем, что карта не является shiny и уникальна
                    if not card.shiny and not any(c.id == card.id for c in daily_cards):
                        daily_cards.append(card)
                except Exception as e:
                    logger.warning(
        f"Не удалось сгенерировать карточку (попытка {attempts}): {str(e)}")
                    continue

            if len(daily_cards) >= 4:
                return daily_cards
            else:
                logger.warning(
f"Не удалось получить достаточно карточек после {attempts} попыток, используем резервный метод")

                # Резервный метод: случайный выбор, если random_card не сработал
                # Гарантированно выбираем только не-shiny карты
                cards = await self.__session.scalars(select(Card)
                                                    .filter_by(shiny=False))
                cards = cards.all()

                if len(cards) >= 4:
                    # Используем множество для отслеживания уникальных карт
                    unique_cards = []
                    used_ids = set()
                    for card in cards:
                        if card.id not in used_ids:
                            unique_cards.append(card)
                            used_ids.add(card.id)
                            if len(unique_cards) >= 4:
                                break
                    return unique_cards[:4]
                else:
                    logger.warning(
                "Недостаточно карточек в базе данных для ежедневного магазина")
                    return []

        except Exception as exc:
            logger.exception(
            f"Ошибка при получении карточек для ежедневного магазина: {exc}")
            return []

    async def add_referral(self,
                        referral_id: int, referrer_id: int,
                        referrer_reward: int = 0) -> Referrals | None:
        """Создаёт рефералов"""
        if referral_id != referrer_id:
            existing_referral = await self.__session.scalar(
                select(Referrals).filter_by(user_id=referrer_id,
                                            referral_id=referral_id)
            )
            if not existing_referral:
                referrer = await self.get_user(referrer_id)
                if referrer:
                    referral_object = Referrals(
                        user_id=referrer_id,
                        referral_id=referral_id,
                        referrer_reward=referrer_reward
                    )
                    self.__session.add(referral_object)
                    await self.__session.commit()
                    return referral_object
        return None

    async def get_award(self,
                        referrer_id: int, award: int) -> bool:
        """Выдаёт награду за реферала"""
        try:
            referrer = await self.get_user(referrer_id)
            if referrer:
                referrer.balance += award
                await self.__session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при начислении награды за реферала: {e}")
            return False

    async def create_clan(self, name: str, tag: str, description: str,
                        user_id: int):
        """Создаёт клан по данным юзера"""
        from app.func import MSK_TIMEZONE
        time = datetime.now(MSK_TIMEZONE)
        clan = Clan(name=name, tag=tag, description=description,
                    created_at=time, leader_id=user_id)
        self.__session.add(clan)
        member = ClanMember(user_id=user_id, clan_id=clan.id,
                            joined_at=time, is_leader=True)
        clan.members.append(member)
        self.__session.add(member)
        await self.__session.commit()
        logger.info(f"Создан клан {tag}")

    async def get_clan_invitation(self, clan_id: int,
                                receiver_id: int) -> ClanInvitation | None:
        """Проверяет существование приглашения в клан для пользователя"""
        try:
            return await self.__session.scalar(
                select(ClanInvitation)
                .filter_by(clan_id=clan_id, receiver_id=receiver_id)
            )
        except Exception as exc:
            logger.exception(
f"Ошибка при проверке приглашения в клан для пользователя id={receiver_id}: {exc}")
            return None

    async def create_clan_invitation(self,clan_id: int, sender_id: int,
                                    receiver_id: int) -> ClanInvitation | None:
        """Создает новое приглашение в клан"""
        try:
            existing_invitation = await self.get_clan_invitation(clan_id,
                                                                receiver_id)
            if existing_invitation:
                return None

            from app.func import MSK_TIMEZONE
            invitation = ClanInvitation(
                clan_id=clan_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                sent_at=datetime.now(MSK_TIMEZONE)
            )
            self.__session.add(invitation)
            await self.__session.commit()
            logger.info(
        f"Создано приглашение в клан {clan_id} для пользователя {receiver_id}")
            return invitation
        except Exception as exc:
            logger.exception(
f"Ошибка при создании приглашения в клан для пользователя id={receiver_id}: {exc}")
            return None
    
    async def create_clan_member(self,user_id:int, clan_id: int) -> ClanMember:
        user = await self.get_user(user_id)
        clan = await self.get_clan(clan_id)

        from app.func import MSK_TIMEZONE
        clan_member = ClanMember(user_id=user_id,
                                clan_id=clan_id,
                                joined_at=datetime.now(MSK_TIMEZONE),
                                contribution=0,
                                is_leader=False)
        self.__session.add(clan_member)

        user.clan_member = clan_member
        clan.members.append(clan_member)

        await self.__session.commit()
        return clan_member

    async def delete_member(self, user_id: int):
        user = await self.get_user(user_id)
        
        clan_member = user.clan_member
        user.clan_member = None
        await self.__session.delete(clan_member)
        await self.__session.commit()
    

    async def delete_clan(self,clan_id):
        clan = await self.get_clan(clan_id)

        [await self.delete_member(member.user_id) for member in clan.members]
        
        await self.__session.delete(clan)
        await self.__session.commit()

    async def get_promo(self, promocode: str) -> Promo | None:
        from app.func import MSK_TIMEZONE
        from datetime import datetime

        promo = await self.__session.scalar(select(Promo).filter_by(promocode=promocode))

        # Проверяем, что промокод не истёк
        if promo and promo.expire_at < datetime.now(MSK_TIMEZONE):
            return None  # Промокод истёк

        return promo  # Промокод действующий

    async def create_promo(self, promocode: str, reward: int, days_until_expire: int) -> Promo | None:
        """Создаёт новый промокод"""
        from app.func import MSK_TIMEZONE
        from datetime import datetime, timedelta

        try:
            # Проверяем, что промокод с таким кодом не существует
            existing_promo = await self.get_promo(promocode)
            if existing_promo:
                return None  # Промокод с таким кодом уже существует

            # Вычисляем дату истечения
            expire_at = datetime.now(MSK_TIMEZONE) + timedelta(days=days_until_expire)

            # Создаём промокод
            promo = Promo(
                promocode=promocode,
                reward=reward,
                expire_at=expire_at
            )

            self.__session.add(promo)
            await self.__session.commit()

            return promo

        except Exception as exc:
            logger.exception(f"Ошибка при создании промокода: {exc}")
            return None

    async def create_trade(self, user_id:int, card_id:int):
        trade = Trade(user_id=user_id,card_id=card_id)

        self.__session.add(trade)
        await self.__session.commit()

        return trade

    async def get_trade(self,user_id:int) -> Trade | None:
        return await self.__session.scalar(select(Trade).filter_by(
                            user_id=user_id))

    async def delete_trade(self, user_id: int):
        await self.__session.delete(await self.get_trade(user_id))
        await self.__session.commit()

    async def get_card(self, card_id:int):
        try:
            return await self.__session.scalar(select(Card).filter_by(
                id=card_id))
        except Exception as exc:
            logger.exception(f"Ошибка получения карты: {exc}")

            return None
    
    async def complete_trade(self, trade: Trade):
        try:
            user1 = await self.get_user(trade.user_id)
            user2 = await self.get_user(trade.partner_id)
            
            card1 = await self.get_card(trade.card_id)
            card2 = await self.get_card(trade.partner_card)

            # Проверяем, что обе карты существуют
            if not card1 or not card2:
                return False

            # Проверяем, что карты есть в инвентаре пользователей
            if card1 not in user1.inventory or card2 not in user2.inventory:
                return False

            # Удаляем карты из инвентаря
            user1.inventory.remove(card1)
            user2.inventory.remove(card2)
            
            # Добавляем карты в инвентарь
            user1.inventory.append(card2)
            user2.inventory.append(card1)

            await self.__session.commit()
            await self.delete_trade(trade.user_id)
            return True

        except Exception as exc:
            logger.exception(f"Ошибка при завершении трейда: {exc}")
            return False

class RedisRequests:

    async def daily_verse() -> int:
        session = None
        try:
            session = Redis()
            verse = await session.get('daily_verse')
            if verse:
                return int(verse.decode('utf-8'))
            return None
        except Exception as exc:
            logger.exception(f"Ошибка при получении ежедневной вселенной из Redis: {exc}")
            return None
        finally:
            if session:
                await session.aclose()

    async def daily_items() -> str:
        session = Redis()
        items = await session.get('shop_items') or None
        await session.aclose()
        return items
