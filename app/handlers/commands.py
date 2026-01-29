# Стандартные библиотеки
from datetime import datetime, timedelta, timezone, timedelta
from html import escape
import math
import random

# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Сторонние библиотеки
from aiogram import Router,F
from aiogram.filters import CommandStart,CommandObject,Command
from aiogram.types import Message,FSInputFile
from aiogram.utils.markdown import html_decoration
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Локальные импорты
from app.filters import Private
from app.func import user_photo_link, random_card
from app.keyboards import main_kb
from app.messages import MText
from db import Referrals, User, Verse,RedisRequests, DB

#Игроки, которые открывают карту, пока она обрабатывается
user_card_opens = []

router = Router()

@router.message(CommandStart(),Private())
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user = await message.bot.get_chat(message.from_user.id)
    
    
    db = DB(session)
    user, action = await db.create_or_update_user(user.id,
                                message.from_user.username,
                                user.full_name,
                                user.bio)

    if command.args:
        option,value = command.args.split("_")
        match option:
            case "r":
                try:
                    inviter_id = int(value)
                except:
                    inviter_id = None

                if not inviter_id:
                    await message.answer(MText.get("not_user_id"))
                    return

                if not inviter_id != message.from_user.id:
                    await message.answer(MText.get("u_cant_be_referral"))
                    return

                if not action:
                    await message.answer(MText.get("only_new_users"))
                    return

                inviter = await db.get_user(inviter_id)
                if not inviter:
                    await message.answer(MText.get("not_user_id"))
                    return
                    
                # Добавляем реферальную связь
                referral = await db.add_referral(referral_id=user.id,
                                                referrer_id=inviter_id)
                if not referral:
                    await message.answer(MText.get("sorry"))
                    return
                    
                
                reward_amount = random.randint(50, 300) if not inviter.vip else random.randint(150, 700)

                # Награждаем реферрера за реферала
                await db.get_award(inviter_id, reward_amount)
                
                referrer_link = f'<a href="tg://user?id={inviter.id}">{html_decoration.quote(inviter.name)}</a>'
                new_user_link = f'<a href="tg://user?id={user.id}">{html_decoration.quote(user.name)}</a>'

                await message.reply(MText.get("referral_welcome").format(
                    referrer_link=referrer_link))

                try:
                    await message.bot.send_message(
                        inviter.id,
                        MText.get("new_referral").format(link=new_user_link)
                        )
                    await message.bot.send_message(
                            inviter.id,
                            MText.get("reward_message").format(
                                reward=reward_amount,
                                yens=inviter.yens+reward_amount)
                            )
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")

    message_text = MText.get("start")
    keyboard = await main_kb()
    await message.reply(message_text, reply_markup=keyboard)


@router.message(Command("card"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
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

@router.message(Command("profile"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    db = DB(session)
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
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        await message.reply(MText.get("not_user").format(name = escape(user.name)))

@router.message(Command("daily"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    try:
        # Получаем ID текущей ежедневной вселенной из Redis
        verse_id = await RedisRequests.daily_verse()

        if not verse_id:
            await message.reply(MText.get("daily_verse_error"))
            return
        # Получаем информацию о вселенной из базы данных
        db = DB(session)
        verse = await db.get_verse(verse_id)

        if verse:
            # Форматируем сообщение с информацией о ежедневной вселенной
            text = MText.get("daily_verse").format(verse=verse.name)
            await message.reply(text)
        else:
            await message.reply(MText.get("daily_verse_error"))
    except Exception as e:
        logger.error(f"Ошибка при получении ежедневной вселенной: {str(e)}", exc_info=True)
        await message.reply(MText.get("daily_verse_error"))

@router.message(Command("reload"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    if message.from_user.id == 5027089008:
        MText.reload()