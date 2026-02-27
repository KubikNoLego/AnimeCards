from html import escape

from aiogram import Router,F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.StateGroups import ClanLeader,CreateClan
from app.filters import Private
from app.keyboards import (
    clan_invite_kb, clan_leader, clan_create,
    clan_create_exit, clan_member, create_clan
                        )
from app.messages import MText
from app.func import MSK_TIMEZONE
from db import DB, Clan


router = Router()

@router.message(ClanLeader.desc)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if len(message.text) <= 255:
        clan = await db.get_clan(user.clan_member.clan_id)
        clan.description = message.text
        await session.commit()
        await state.clear()
        await message.delete()
        await message.answer(MText.get("clan_change_desc_succses"))
    else:
        await message.answer(MText.get("clan_description_too_long").format(
            desc=len(message.text))
            )

@router.message(CreateClan.name)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    clan = await session.scalar(select(Clan).filter_by(
        name=escape(message.text))
        )
    if len(message.text) <= 50 and not clan:
        await state.update_data(name=escape(message.text))
        await state.set_state(CreateClan.tag)
        await message.answer(MText.get("clan_tag_prompt"),
                            reply_markup= await clan_create_exit())
    else:
        await message.answer(MText.get("clan_name_too_long").format(
            name=len(message.text))
            )

@router.message(CreateClan.tag)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    clan = await session.scalar(select(Clan).filter_by(
        tag = escape(message.text)))
    if len(message.text) <= 5 and not clan:
        await state.update_data(tag=escape(message.text))
        await state.set_state(CreateClan.description)
        await message.answer(MText.get("clan_description_prompt"),
                            reply_markup=await clan_create_exit())
    else:
        await message.answer(MText.get("clan_tag_too_long").format(
            tag=len(message.text))
            )

@router.message(CreateClan.description)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    if len(message.text) <= 255:
        await state.update_data(description = escape(message.text))
        data = await state.get_data()
        await state.set_state(CreateClan.accept)
        await message.answer(MText.get("clan_creation_confirmation").format(
            name=data['name'], tag=data['tag'], desc=data['description']),
            reply_markup= await clan_create())
    else:
        await message.answer(MText.get("clan_description_too_long").format(
            desc=len(message.text)))

@router.message(F.text == "🛡️ Клан",Private())
async def _(message:Message, session:AsyncSession):
    db = DB(session)

    user = await db.get_user(message.from_user.id)
    if user and user.clan_member:
        clan = await db.get_clan(user.clan_member.clan_id)
        member = user.clan_member

        # Собираем информацию о клане
        clan_info = MText.get("clan_message").format(name = clan.name,
                                                    tag = clan.tag,
                                                    members = len(clan.members),
                                                    balance = clan.balance,
        created_at = clan.created_at.astimezone(MSK_TIMEZONE)
        .strftime('%d.%m.%Y %H:%M'),
        link = f'<a href="tg://user?id={clan.leader_id}">{escape(clan.leader.name)}</a>',
        role = '👑 Лидер' if member.is_leader else '👥 Участник',
        contribution = member.contribution,
        joined_at = member.joined_at.astimezone(MSK_TIMEZONE).strftime('%d.%m.%Y %H:%M'),
        desc = clan.description if clan.description else 'Нет описания')
        
        await message.reply(clan_info,reply_markup= await clan_member() if 
                            not member.is_leader else await clan_leader())
    else:
        await message.reply(MText.get("not_in_clan"), reply_markup= None if 
                            not user.vip else await create_clan())