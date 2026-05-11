from random import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.requests import DB
from app.utils.consts import CLAN_CREATION_COST
from app.utils.enums.clan_enums import ClanActions, ClanInviteResult, ClanKick, CreateClanResult


async def get_member_page(db: DB, page: int, user_id: int):
    user = await db.user.get_user(user_id)

    if not user:
        return None
    
    clan = await db.clan.get_clan(user.clan_member.clan_id)

    members = [m for m in clan.members if m.user_id != user_id]

    if not members: return {'empty': True}

    return {'empty': False,
            'member': members[page-1],
            'total': len(members),
            'is_leader': user.clan_member.is_leader
            }

async def leave_clan_user(session: AsyncSession, user_id: int):
    db = DB(session)

    user = await db.user.get_user(user_id)

    if not user or not user.clan_member:
        return

    clan_id = user.clan_member.clan_id
    is_leader = user.clan_member.is_leader

    await db.clan.delete_member(user_id)

    if is_leader:
        clan = await db.clan.get_clan(clan_id)

        if clan.members:
            new_leader = random.choice(clan.members)

            new_leader.is_leader = True
            clan.leader_id = new_leader.user_id

        else:
            await db.clan.delete_clan(clan_id)

    await session.commit()

    return True

async def kick_member(db: DB, target_id: int, leader_id: int):

    leader = await db.user.get_user(leader_id)
    target = await db.user.get_user(target_id)

    if not leader or not leader.clan_member:
        return ClanKick.NO_LEADER
    
    if not leader.clan_member.is_leader:
        return ClanKick.NO_PERMS
    
    if not target or not target.clan_member:
        return ClanKick.NO_TARGET
    
    if leader.id == target.id:
        return ClanKick.SELF_KICK
    
    if (leader.clan_member.clan_id
        != target.clan_member.clan_id):
        return ClanKick.WRONG_CLAN
    
    if target.clan_member.is_leader:
        return ClanKick.TARGET_LEADER
    
    await db.clan.delete_member(target.id)

    return target

async def handle_invite(db: DB, session: AsyncSession,
        user_id: int, clan_id: int, action: ClanActions):
        user = await db.user.get_user(user_id)

        if user.clan_member:
            return ClanInviteResult.ALREADY_IN_CLAN

        invite = await db.clan.get_clan_invitation(clan_id, user_id)

        if not invite:
            return ClanInviteResult.NOT_FOUND

        if action == ClanActions.ACCEPT:
            await db.clan.create_clan_member(user_id, clan_id)
            result = ClanInviteResult.ACCEPTED

        else:
            result = ClanInviteResult.DECLINED

        await session.delete(invite)
        await session.commit()

        return result

async def create_clan_service(
        db: DB,
        session: AsyncSession,
        user_id: int,
        data: dict
    ):
        user = await db.user.get_user(user_id)

        if user.clan_member:
            return CreateClanResult.ALREADY_IN_CLAN

        if user.balance < CLAN_CREATION_COST:
            return CreateClanResult.NOT_ENOUGH_YENS

        required = ("name", "tag", "description")

        if not all(key in data for key in required):
            return CreateClanResult.INVALID_STATE

        async with session.begin():

            user.balance -= CLAN_CREATION_COST

            await db.clan.create_clan(
                data["name"],
                data["tag"],
                data["description"],
                user_id
            )

        return CreateClanResult.SUCCESS

async def invite_member(db: DB,
            sender_id: int, target_id: int, chat_type: str, is_reply: bool):
        sender = await db.user.get_user(sender_id)

        if (not sender
            or not sender.clan_member
            or not sender.clan_member.is_leader):

            return ClanInviteResult.NOT_LEADER

        if chat_type == "private":
            return ClanInviteResult.PRIVATE_CHAT

        if not is_reply:
            return ClanInviteResult.NO_REPLY

        if sender_id == target_id:
            return ClanInviteResult.SELF_INVITE

        target = await db.user.get_user(target_id)

        if not target:
            return ClanInviteResult.USER_NOT_FOUND

        if target.clan_member:
            return ClanInviteResult.USER_ALREADY_IN_CLAN

        invitation = await db.clan.get_clan_invitation(
                                        sender.clan_member.clan_id, target.id)

        if invitation:
            return ClanInviteResult.INVITE_ALREADY_EXISTS

        await db.clan.create_clan_invitation(
            sender.clan_member.clan_id,
            sender.id,
            target.id)

        return {
            "result": ClanInviteResult.SUCCESS,
            "sender": sender,
            "target": target}