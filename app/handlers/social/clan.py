from html import escape
import random

from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.keyboards.inline.datas import ClanKickData
from app.services.clan_service import create_clan_service, get_member_page, handle_invite, invite_member, kick_member, leave_clan_user
from app.services.profile import user_photo_link
from app.states.states import ChangeDescribe, ClanLeader,CreateClan
from app.filters import Private
from app.keyboards import (
    clan_invite_kb, clan_leader, clan_create,
    clan_create_exit, clan_member, create_clan
                        )
from app.keyboards import (member_pagination_keyboard, ClanInvite, 
                        MemberPagination)
from app.messages import MText
from app.utils import MSK_TIMEZONE
from app.database import DB, Clan
from app.utils.clan_pagination_message import edit_message
from app.utils.consts import CLAN_CREATION_COST
from app.utils.enums.clan_enums import ClanActions, ClanInviteResult, ClanKick, CreateClanResult


router = Router()


@router.callback_query(F.data.startswith("delete_clan"))
async def _(callback:CallbackQuery, session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(callback.from_user.id)
    if user.clan_member.is_leader:
        await db.clan.delete_clan(user.clan_member.clan_id)
        
        await callback.message.delete()
        await callback.answer("Вы удалили клан")
    
    await callback.answer()

@router.callback_query(F.data == "change_desc_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(MText.get("clan_change_desc"))
    await state.set_state(ClanLeader.desc)

    await callback.answer()

@router.callback_query(F.data.startswith("leave_clan"))
async def _(callback:CallbackQuery, session: AsyncSession):
    await leave_clan_user(session, callback.from_user.id)
    
    await callback.message.delete()
    await callback.answer("Вы покинули клан")

@router.callback_query(ClanKickData.filter())
async def _(callback:CallbackQuery, callback_data: ClanKickData,session: AsyncSession):
    user_id = callback_data.user_id
    
    db = DB(session)
    result = await kick_member(
        db,
        user_id,
        callback.from_user.id)

    if isinstance(result, ClanKick):
        return await callback.answer(
            result.value,
            show_alert=True)

    await callback.message.delete()

    await callback.answer(show_alert=True, text="Пользователь исключён")

    try:

        await callback.bot.send_message(
            result.id,
            MText.get("u_have_been_kicked"))
        
    except Exception:
        pass

@router.callback_query(MemberPagination.filter())
async def _(callback:CallbackQuery,callback_data: MemberPagination,
            session: AsyncSession):
    page = callback_data.p

    db = DB(session)

    data = await get_member_page(db, page, callback.from_user.id)

    if not data:
        return await callback.answer()

    if data['empty']:
        return await edit_message(
            callback.message,
            MText.get("clan_no_members")
        )

    member = data['member']

    text = MText.get("clan_member_info").format(
        member_name=escape(member.user.name),
        join_date=member.joined_at.astimezone(MSK_TIMEZONE)
            .strftime('%d.%m.%Y %H:%M'),
        contribution=member.contribution
    )

    keyboard = await member_pagination_keyboard(page,
        data['total'], member.user.id, data['is_leader'])

    photo = await user_photo_link(callback.bot, member.user.id)

    await edit_message(callback.message, text, keyboard, photo)

    await callback.answer()

@router.callback_query(ClanInvite.filter())
async def _(callback:CallbackQuery,callback_data: ClanInvite,
            session: AsyncSession):
    db = DB(session)

    result = await handle_invite(db=db, session=session,
                                user_id=callback.from_user.id,
                                clan_id=callback_data.clan_id,
                                action=ClanActions(callback_data.act))

    await callback.message.delete()

    await callback.answer(
        result.value,
        show_alert=True
    )

@router.callback_query(F.data == "accept_create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)

    result = await create_clan_service(
        db=db,
        session=session,
        user_id=callback.from_user.id,
        data=await state.get_data()
    )

    if result != CreateClanResult.SUCCESS:
        return await callback.answer(
            result.value,
            show_alert=True
        )

    await callback.message.delete()

    await callback.answer(
        f"{result.value}! Списано {CLAN_CREATION_COST} ¥"
    )

    await state.clear()

@router.callback_query(F.data == "cancel_create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик кнопки отмены создания клана"""
    # Очищаем состояние пользователя
    await state.clear()
    await callback.message.delete()
    await callback.answer("Создание клана отменено")

@router.callback_query(F.data == "create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)

    user = await db.user.get_user(
        callback.from_user.id
    )

    if user.balance < CLAN_CREATION_COST:
        return await callback.answer(
            MText.get("not_enough_yens_clan"),
            show_alert=True
        )

    await state.set_state(CreateClan.name)

    await callback.message.answer(
        MText.get("clan_name_prompt"),
        reply_markup=await clan_create_exit()
    )

    await callback.answer()

@router.message(Command("пригласить",prefix="."))
async def _(message: Message, session:AsyncSession):
    db = DB(session)

    target_id = (
        message.reply_to_message.from_user.id
        if message.reply_to_message
        else None)

    result = await invite_member(
        db=db,
        sender_id=message.from_user.id,
        target_id=target_id,
        chat_type=message.chat.type,
        is_reply=bool(message.reply_to_message))

    if isinstance(result, ClanInviteResult):
        return await message.reply(result.value)

    sender = result["sender"]
    target = result["target"]

    await message.reply(
        ClanInviteResult.SUCCESS.value)

    try:
        await message.bot.send_message(
            target.id,
            text=MText.get("clan_invite_prompt").format(
                clan=sender.clan_member.clan.name
            ),
            reply_markup=await clan_invite_kb(
                sender.clan_member.clan_id
            ))

    except Exception:
        logger.exception("Ошибка отправки инвайта")

@router.message(ClanLeader.desc)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if len(message.text) <= 255:
        clan = await db.clan.get_clan(user.clan_member.clan_id)
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

    user = await db.user.get_user(message.from_user.id)
    if user and user.clan_member:
        clan = await db.clan.get_clan(user.clan_member.clan_id)
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