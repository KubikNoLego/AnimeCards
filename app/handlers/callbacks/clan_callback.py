from html import escape
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import clan_create_exit, member_pagination_keyboard
from app.messages import MText
from app.keyboards import ClanInvite,MemberPagination
from app.StateGroups.states import ChangeDescribe,CreateClan,ClanLeader
from app.func import MSK_TIMEZONE
from db import DB


router = Router()


@router.callback_query(F.data.startswith("delete_clan"))
async def _(callback:CallbackQuery, session: AsyncSession):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)
    if user.clan_member.is_leader:
        await db.delete_clan(user.clan_member.clan_id)
        
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
    db = DB(session)
    user = await db.get_user(callback.from_user.id)
    if user.clan_member and user.clan_member.is_leader:
        clan = await db.get_clan(user.clan_member.clan_id)
        
        await db.delete_member(user.id)
        
        new_leader = random.choice(clan.members)
        new_leader.is_leader = True
        clan.leader_id = new_leader.user_id

        await session.commit()

        await callback.message.delete()
    elif user.clan_member:
        await db.delete_member(user.id)
        await callback.message.delete()
    await callback.answer("Вы покинули клан")

@router.callback_query(F.data.startswith("kick_"))
async def _(callback:CallbackQuery, session: AsyncSession):
    user_id = int(callback.data.split("_")[1])
    
    db = DB(session)
    user = await db.get_user(user_id)

    moder = await db.get_user(callback.from_user.id)
    clan = await db.get_clan(moder.clan_member.clan_id)

    if user.clan_member not in clan.members:
        return

    await db.delete_member(user.id)
    await callback.message.delete()
    await callback.answer("Вы успешно выгнали пользователя")
    await callback.message.bot.send_message(user_id,MText.get(
        "u_have_been_kicked"))

    await callback.answer()

@router.callback_query(MemberPagination.filter())
async def _(callback:CallbackQuery,callback_data: MemberPagination,
            session: AsyncSession):
    page = callback_data.p

    db = DB(session)

    user = await db.get_user(callback.from_user.id)

    if not user:
        return

    clan = await db.get_clan(user.clan_member.clan_id)

    clan_members = clan.members
    clan_members.remove(user.clan_member)

    # Проверяем, есть ли участники в клане (кроме лидера)
    if not clan_members:
        await callback.message.edit_text(text=MText.get("clan_no_members"))
        return

    current_member = (clan_members[page-1].user, clan_members[page-1])

    # Форматируем информацию об участнике
    member_info = MText.get("clan_member_info").format(
        member_name=escape(current_member[0].name),
        join_date=current_member[1].joined_at.astimezone(MSK_TIMEZONE)
            .strftime('%d.%m.%Y %H:%M'),
        contribution=current_member[1].contribution
    )

    profile_photos = await callback.message.bot.get_user_profile_photos(
        current_member[0].id, limit=1)
    photo = profile_photos.photos[0][-1].file_id if profile_photos and len(
        profile_photos.photos) > 0 else None

    if photo:
        await callback.message.edit_media(media=InputMediaPhoto(media=photo),
    reply_markup=await member_pagination_keyboard(page,
        len(clan_members), current_member[0].id,user.clan_member.is_leader))
        await callback.message.edit_caption(caption=member_info,
    reply_markup=await member_pagination_keyboard(page,
        len(clan_members), current_member[0].id,user.clan_member.is_leader))
    else:
        await callback.message.edit_text(text=member_info,
    reply_markup=await member_pagination_keyboard(page,
        len(clan_members), current_member[0].id,user.clan_member.is_leader))

    await callback.answer()

@router.callback_query(ClanInvite.filter())
async def _(callback:CallbackQuery,callback_data: ClanInvite,
            session: AsyncSession):
    clan_id,action = callback_data.clan_id,callback_data.act

    db = DB(session)

    match action:
        case 1:
            member = await db.create_clan_member(callback.from_user.id, clan_id)

            await callback.message.delete()
            await callback.message.answer("Приглашение принято")

            invite = await db.get_clan_invitation(clan_id,callback.from_user.id)

            await session.delete(invite)
            await session.commit()


        case 0:
            invite = await db.get_clan_invitation(clan_id,callback.from_user.id)

            await session.delete(invite)
            await session.commit()

            await callback.message.delete()
            await callback.answer("Приглашение отклонено")
    
    await callback.answer()

@router.callback_query(F.data == "accept_create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)

    # Проверяем, достаточно ли у пользователя йен для создания клана
    clan_creation_cost = 1000
    if user.balance < clan_creation_cost:
        await callback.answer(MText.get("not_enough_yens_clan"),
                            show_alert=True)
        return

    data = await state.get_data()

    # Списываем йены за создание клана
    user.balance -= clan_creation_cost
    await session.commit()

    await db.create_clan(data['name'],data['tag'],data['description'],
                        callback.from_user.id)
    await callback.message.delete()
    await callback.answer(
        "Клан успешно создан! Списано {clan_creation_cost} ¥")
    
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
    user = await db.get_user(callback.from_user.id)

    # Проверяем баланс пользователя перед созданием клана
    clan_creation_cost = 1000
    if user.balance < clan_creation_cost:
        await callback.answer(MText.get("not_enough_yens_clan"),
                            show_alert=True)
        return

    await state.set_state(CreateClan.name)
    await callback.message.answer(MText.get("clan_name_prompt"),
                                reply_markup=await clan_create_exit())
    
    await callback.answer()

@router.callback_query(F.data == "delete_describe")
async def delete_describe_user(callback: CallbackQuery,session : AsyncSession):
    await callback.message.answer(MText.get("describe_updated_empty"))
    user = await DB(session).get_user(callback.from_user.id)
    user.profile.describe = ""
    await session.commit()

    await callback.answer()

@router.callback_query(F.data == "change_describe")
async def change_describe_user(callback: CallbackQuery, session: AsyncSession,
                            state:FSMContext):
    await state.set_state(ChangeDescribe.text)
    await callback.message.answer(MText.get("change_describe_prompt"))

    await callback.answer()