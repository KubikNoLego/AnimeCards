from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from db.models import Clan, ClanMember, ClanInvitation, User
from app.func.consts import MSK_TIMEZONE


class ClanRepo:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_clan(self, clan_id: int) -> Clan | None:
        """Получает клан из БД, если он есть"""
        try:
            return await self.session.scalar(select(Clan)
                                    .filter_by(id=clan_id))
        except Exception as exc:
            logger.exception(
                f"Ошибка при получении клана id={clan_id}: {exc}")
            return None

    async def create_clan(self, name: str, tag: str, description: str,
                    user_id: int):
        """Создаёт клан по данным юзера"""
        time = datetime.now(MSK_TIMEZONE)
        clan = Clan(name=name, tag=tag, description=description,
                    created_at=time, leader_id=user_id)
        self.session.add(clan)
        member = ClanMember(user_id=user_id, clan_id=clan.id,
                            joined_at=time, is_leader=True)
        clan.members.append(member)
        self.session.add(member)
        await self.session.commit()
        logger.info(f"Создан клан {tag}")

    async def get_clan_invitation(self, clan_id: int,
                        receiver_id: int) -> ClanInvitation | None:
        """Проверяет существование приглашения в клан для пользователя"""
        try:
            return await self.session.scalar(
                select(ClanInvitation)
                .filter_by(clan_id=clan_id, receiver_id=receiver_id)
            )
        except Exception as exc:
            logger.exception(
                f"Ошибка при проверке приглашения в клан для пользователя id={receiver_id}: {exc}")
            return None

    async def create_clan_invitation(self, clan_id: int, sender_id: int,
                    receiver_id: int) -> ClanInvitation | None:
        """Создает новое приглашение в клан"""
        try:
            existing_invitation = await self.get_clan_invitation(clan_id,
                                            receiver_id)
            if existing_invitation:
                return None

            invitation = ClanInvitation(
                clan_id=clan_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                sent_at=datetime.now(MSK_TIMEZONE)
            )
            self.session.add(invitation)
            await self.session.commit()
            logger.info(
                f"Создано приглашение в клан {clan_id} для пользователя {receiver_id}")
            return invitation
        except Exception as exc:
            logger.exception(
                f"Ошибка при создании приглашения в клан для пользователя id={receiver_id}: {exc}")
            return None

    async def create_clan_member(self, user_id: int, clan_id: int) -> ClanMember:
        """Создаёт участника клана"""
        user = await self.session.scalar(select(User).filter_by(id=user_id))
        clan = await self.get_clan(clan_id)

        clan_member = ClanMember(user_id=user_id,
                                clan_id=clan_id,
                                joined_at=datetime.now(MSK_TIMEZONE),
                                contribution=0,
                                is_leader=False)
        self.session.add(clan_member)

        user.clan_member = clan_member
        clan.members.append(clan_member)

        await self.session.commit()
        return clan_member

    async def delete_member(self, user_id: int):
        """Удаляет участника из клана"""
        user = await self.session.scalar(select(User).filter_by(id=user_id))

        clan_member = user.clan_member
        user.clan_member = None
        await self.session.delete(clan_member)
        await self.session.commit()

    async def delete_clan(self, clan_id: int):
        """Удаляет клан"""
        clan = await self.get_clan(clan_id)

        for member in clan.members:
            await self.delete_member(member.user_id)

        await self.session.delete(clan)
        await self.session.commit()