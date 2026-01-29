# Стандартные библиотеки
from datetime import datetime, timedelta, timezone, timedelta
import math
from html import escape
import re
import os


# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Сторонние библиотеки
from aiogram import Router,F
from aiogram.types import Message,FSInputFile
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# Локальные импорты
from app.StateGroups.states import ChangeDescribe,CreateClan,ClanLeader
from app.filters import ProfileFilter, Private
from app.func import random_card, user_photo_link, create_qr
from app.messages import MText
from app.keyboards import profile_keyboard, shop_keyboard,clan_create_exit,create_clan,clan_invite_kb,clan_create,clan_leader,clan_member
from db import Card, Clan, ClanMember, User,RedisRequests,DB

router = Router()


user_card_opens = []


@router.message(F.text == ".пригласить")
async def _(message: Message, session:AsyncSession,state:FSMContext):
    db = DB(session)
    sender = await db.get_user(message.from_user.id)

    # Проверка, является ли пользователь лидером клана
    if not sender.clan_member or sender.clan_member.clan.leader_id != sender.id:
        await message.reply(MText.get("not_clan_leader"))
        return

    # Проверка, что команда используется в групповом чате и как ответ на сообщение
    if message.chat.type == "private":
        await message.reply(MText.get("not_in_private_chat"))
        return

    if not message.reply_to_message:
        await message.reply(MText.get("not_in_private_chat"))
        return

    # Получаем пользователя, которого приглашаем
    user = await db.get_user(message.reply_to_message.from_user.id)
    if not user:
        await message.reply(MText.get("not_user"))
        return

    # Проверка, что пользователь не состоит в клане
    if user.clan_member:
        await message.reply(MText.get("user_already_in_clan"))
        return

    # Проверяем, не отправляли ли мы уже приглашение этому пользователю
    existing_invitation = await db.get_clan_invitation(sender.clan_member.clan.id, user.id)
    if existing_invitation:
        await message.reply(MText.get("clan_invite_already_sent"))
        return

    # Создаем приглашение в базе данных
    invitation = await db.create_clan_invitation(sender.clan_member.clan.id, sender.id, user.id)
    if not invitation:
        await message.reply(MText.get("clan_invite_already_sent"))
        return

    # Отправляем приглашение
    try:
        await message.reply(MText.get("clan_invite_success"))
        await message.bot.send_message(user.id,
                        text=MText.get("clan_invite_prompt")
                        .format(clan=sender.clan_member.clan.name),
                        reply_markup= await clan_invite_kb(sender.clan_member.clan_id))
    except Exception as e:
        logger.error(f"Ошибка при отправке приглашения: {str(e)}", exc_info=True)
        await message.answer(MText.get("invite_send_error"))

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
        await message.answer(MText.get("clan_description_too_long").format(desc=len(message.text)))

@router.message(CreateClan.name)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    clan = await session.scalar(select(Clan).filter_by(
        name=escape(message.text))
        )
    if len(message.text) <= 50 and not clan:
        await state.update_data(name=escape(message.text))
        await state.set_state(CreateClan.tag)
        await message.answer(MText.get("clan_tag_prompt"), reply_markup=await clan_create_exit())
    else:
        await message.answer(MText.get("clan_name_too_long").format(
            name=len(message.text))
            )

@router.message(CreateClan.tag)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    clan = await session.scalar(select(Clan).filter_by(tag = escape(message.text)))
    if len(message.text) <= 5 and not clan:
        await state.update_data(tag=escape(message.text))
        await state.set_state(CreateClan.description)
        await message.answer(MText.get("clan_description_prompt"), reply_markup=await clan_create_exit())
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
        await message.answer(MText.get("clan_creation_confirmation").format(name=data['name'], tag=data['tag'], desc=data['description']), reply_markup= await clan_create())
    else:
        await message.answer(MText.get("clan_description_too_long").format(desc=len(message.text)))

@router.message(F.text == "🛡️ Клан",Private())
async def _(message:Message, session:AsyncSession, state:FSMContext):
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

@router.message(F.text == "🛒 Магазин",Private())
async def _(message:Message,session:AsyncSession):
    items = await RedisRequests.daily_items()
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if items:
        try:
            items = items.decode("utf-8").split(",")
            cards = []

            for item_id in items:
                if item_id.strip():  # Проверяем, что ID не пустой
                    card = await session.scalar(select(Card).filter_by(id=
                                                        int(item_id.strip())))
                    if card:
                        # Применяем 70% надбавку к цене карточки
                        card.value = int(card.value * 1.7)
                        cards.append(card)

            if cards:
                # Создаем клавиатуру с товарами
                keyboard = await shop_keyboard(cards if user.vip else cards[0:3])
                await message.answer(MText.get("daily_shop"), reply_markup=keyboard)
            else:
                await message.answer(MText.get("shop_empty"))
        except Exception as e:
            logger.error(f"Ошибка при обработке магазина: {str(e)}", exc_info=True)
            await message.answer(MText.get("shop_empty"))
    else:
        await message.answer(MText.get("shop_empty"))
        

@router.message(F.text == "🔗 Реферальная ссылка")
async def _(message: Message, session: AsyncSession):
    """Обработчик кнопки реферальной ссылки."""
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        total_reward = 0
        for i in user.referrals:
            total_reward += i.referrer_reward
        # Создаем реферальную ссылку
        bot_info = await message.bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start=r_{user.id}"

        stats_message = MText.get("refferal_text").format(link=referral_link,referral=len(user.referrals),total=total_reward,award="50 до 300" if not user.vip else "150 до 700")
        try:
            qr_file = await create_qr(referral_link)
            try:
                await message.reply_photo(qr_file, caption=stats_message, parse_mode="HTML")
            finally:
                # Удаляем временный файл в любом случае
                if hasattr(qr_file, 'path') and os.path.exists(qr_file.path):
                    os.unlink(qr_file.path)
        except Exception as e:
            await message.reply(MText.get("qr_error"))
    else:
        await message.reply(MText.get("qr_error"))

@router.message(ChangeDescribe.text)
async def _(message:Message, session: AsyncSession, state: FSMContext):
    if len(message.text) > 70:
        await message.answer(MText.get("describe_too_long").format(
            desc = len(message.text)))
    else:
        db = DB(session)
        user = await db.get_user(message.from_user.id)
        user.profile.describe = escape(message.text)
        await session.commit()
        await message.answer(MText.get("describe_updated_success").format(desc= escape(message.text)))
        await state.set_state(None)

@router.message(F.text == "🌐 Открыть карту", Private())
async def _(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_id in user_card_opens:
        await message.reply(MText.get("wait"))
        return

    try:
        
        user_card_opens.append(user_id)
        db = DB(session)
        user = await db.get_user(user_id)
            
        if not user:
            await message.reply(MText.get("not_registered"))
            return
        
        last_open = user.last_open

        if last_open.tzinfo is None:
            last_open = last_open.replace(tzinfo=MSK_TIMEZONE)
            
        hour = 2 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 3

        if (last_open + timedelta(hours=hour) <= datetime.now(MSK_TIMEZONE)) or user.free_open:
            card = await random_card(session,user.pity)
            text = MText.get("card").format(name=card.name,
                                            verse=card.verse_name,
                                            rarity=card.rarity_name,
                                            value=card.value if not user.vip else f"{card.value} (+{math.ceil(card.value * 0.1)})")
            
            text = text + "\n\n✨ Shiny" if card.shiny else text
            
            await message.reply_photo(FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)
            if card not in user.inventory:
                user.inventory.append(card)
            match user.pity:
                case _ if user.pity <= 0:
                    user.pity = 100                    
                case _:
                    user.pity -= 1
            if user.free_open:
                user.free_open -= 1
            else:
                user.last_open = datetime.now(MSK_TIMEZONE)
            added_sum = int(card.value + (math.ceil(card.value * 0.1) if user.vip else 0))
            user.yens += added_sum
            if user.clan_member:
                user.clan_member.contribution += int(added_sum*0.3)
                user.clan_member.clan.balance += int(added_sum*0.3)
            await session.commit()
        else:
            text = MText.nottime(user.last_open)
            await message.reply(text)

    finally:
        # Убираем пользователя из списка после завершения (даже если была ошибка)
        if user_id in user_card_opens:
            user_card_opens.remove(user_id)
    
@router.message(F.text == "🏆 Топ игроков", Private())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        # Получаем топ игроков по балансу (10 человек)
        top_players_balance = await db.get_top_players_by_balance()
        text_balance = MText.top_players_formatter(top_players_balance, user.id)

        # Отправляем только топ по балансу
        await message.answer(text_balance)
    else:
        text = MText.get("not_user").format(name=message.from_user.full_name)
        await message.reply(text)


@router.message(F.text.startswith(".профиль @"))
async def _(message: Message, session: AsyncSession):
    """Обработчик команды .профиль @username - показывает профиль пользователя по username"""
    try:
        # Извлекаем username из команды
        pattern = r'\.профиль @([a-zA-Z0-9_]+)'
        match = re.search(pattern, message.text)

        if not match:
            await message.reply(MText.get("invalid_profile_command"))
            return

        target_username = match.group(1)

        # Ищем пользователя по username
        user = await session.scalar(
            select(User)
            .filter_by(username=target_username)
        )

        if not user:
            await message.reply(MText.get("user_not_found_short"))
            return

        db = DB(session)
        # Получаем информацию о профиле
        place_on_top = await db.get_user_place_on_top(user)
        collections = await db.get_user_collections_count(user)
        text = MText.get("profile").format(
            tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
            name =  escape(user.name),
            balance = user.yens,
            place = place_on_top,
            cards = len(user.inventory),
            collections = collections,
            date = user.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")
        target_profile_photo = None
        try:
            profile_photos = await message.bot.get_user_profile_photos(user.id, limit=1)
            if profile_photos and len(profile_photos.photos) > 0:
                photo = profile_photos.photos[0][-1]
                target_profile_photo = photo.file_id
        except Exception as photo_error:
            logger.error(f"Ошибка при получении фото пользователя {user.id}: {photo_error}")

        if target_profile_photo:
            await message.reply_photo(photo=target_profile_photo, caption=text)
        else:
            await message.reply(text)

    except Exception as e:
        await message.reply(MText.get("profile_error"))

@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    is_reply = message.reply_to_message
    match is_reply:
        case None:
            user = await db.get_user(message.from_user.id)
            if user:
                place_on_top = await db.get_user_place_on_top(user)
                collections = await db.get_user_collections_count(user)
                text = MText.get("profile").format(
                    tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
                    name =  escape(user.name),
                    balance = user.yens,
                    place = place_on_top,
                    cards = len(user.inventory),
                    collections = collections,
                    date = user.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")
                profile_photo = await user_photo_link(message)
                keyboard = await profile_keyboard(user.profile.describe != "")
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text,reply_markup=keyboard)
                else:
                    await message.reply(text,reply_markup=keyboard)
            else:
                text = MText.get("not_user").format(name=escape(message.from_user.full_name))
                await message.reply(text)
        case _:
            user = await db.get_user(message.reply_to_message.from_user.id)
            if user:
                place_on_top = await db.get_user_place_on_top(user)
                collections = await db.get_user_collections_count(user)
                text = MText.get("profile").format(
                    tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
                    name =  escape(user.name),
                    balance = user.yens,
                    place = place_on_top,
                    cards = len(user.inventory),
                    collections = collections,
                    date = user.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")
                profile_photo = await user_photo_link(message)
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text)
                else:
                    await message.reply(text)
            else:
                text = MText.get("not_user").format(name=
                                message.reply_to_message.from_user.full_name)
                await message.reply(text)
