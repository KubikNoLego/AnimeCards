# Стандартные библиотеки
from datetime import datetime, timedelta, timezone
import math
import random

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
from app.func import user_photo_link, random_card, Text,create_qr
from app.keyboards import main_kb
from db import Referrals, User, Verse,RedisRequests, DB

# Глобальный список для отслеживания пользователей, которые открывают карты через команду
user_card_opens = []

router = Router()

@router.message(CommandStart(),Private())
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user = await message.bot.get_chat(message.from_user.id)
    
    
    db = DB(session)
    await db.create_or_update_user(user.id,
                                message.from_user.username,
                                user.full_name,
                                user.bio)
    user = await db.get_user(user.id)

    if command.args:
        option,value = command.args.split("_")
        match option:
            case "r":
                try:
                    inviter_id = int(value)
                except:
                    inviter_id = None

                if inviter_id and inviter_id != message.from_user.id:
                    inviter = await db.get_user(inviter_id)
                    if inviter:
                        # Добавляем реферальную связь
                        referral = await db.add_referral(referral_id=user.id, referrer_id=inviter_id)
                        if referral:
                            # logger.info(f"Добавлен реферал: {inviter_id} -> {user.id}")

                            # Случайная награда от 50 до 300 йен
                            reward_amount = random.randint(50, 300) if not inviter.vip else random.randint(150, 700)

                            # Награждаем реферрера за реферала
                            reward_success = await db.get_award(inviter_id, reward_amount)
                            if reward_success:
                                # logger.info(f"Пользователь {inviter_id} получил {reward_amount} йен за реферала")

                                # Создаем кликабельную ссылку на профиль реферрера
                                referrer_link = f'<a href="tg://user?id={inviter.id}">{html_decoration.quote(inviter.name)}</a>'

                                # Создаем кликабельную ссылку на профиль нового пользователя
                                new_user_link = f'<a href="tg://user?id={user.id}">{html_decoration.quote(user.name)}</a>'

                                messages = Text()._load_messages()
                                await message.reply(messages["referral_welcome"].format(referrer_link=referrer_link))

                                # Отправляем сообщение реферреру о новом реферале
                                try:
                                    # Получаем текущий баланс реферрера для отображения общего количества йен
                                    updated_inviter = await db.get_user(inviter_id)
                                    await message.bot.send_message(
                                        inviter.id,
                                        f"🎉 Новый реферал! {new_user_link} использовал вашу реферальную ссылку!"
                                    )
                                    await message.bot.send_message(
                                        inviter.id,
                                        f"💰 Вы получили {reward_amount} ¥ за приглашение! 💰 Всего у вас: {updated_inviter.yens} ¥"
                                    )
                                except Exception as e:
                                    logger.error(f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")

                                await message.reply(messages["referral_reward_sent"].format(referrer_link=referrer_link, reward_amount=reward_amount))
                            else:
                                # logger.info(f"Пользователь {inviter_id} уже получил награду за этого реферала")

                                # Создаем кликабельную ссылку на профиль реферрера
                                referrer_link = f'<a href="tg://user?id={inviter.id}">{html_decoration.quote(inviter.name)}</a>'

                                # Создаем кликабельную ссылку на профиль нового пользователя
                                new_user_link = f'<a href="tg://user?id={user.id}">{html_decoration.quote(user.name)}</a>'

                                await message.reply(messages["referral_welcome"].format(referrer_link=referrer_link))

                                # Отправляем сообщение реферреру о новом реферале (даже если награда уже была выдана)
                                try:
                                    await message.bot.send_message(
                                        inviter.id,
                                        f"🎉 Новый реферал! {new_user_link} использовал вашу реферальную ссылку!"
                                    )
                                except Exception as e:
                                    logger.error(f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")

                                await message.reply(messages["referral_reward_already_sent"].format(referrer_link=referrer_link))


    message_text = await Text().start_message_generator(user.start if user.start is not None else False)
    keyboard = await main_kb()
    if message_text is None:
        message_text = "Добро пожаловать!"
    await message.reply(message_text, reply_markup=keyboard)


@router.message(Command("card"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user_id = message.from_user.id

    # Проверяем, не открывает ли пользователь карту в данный момент
    if user_id not in user_card_opens:
        user_card_opens.append(user_id)

        try:
            db = DB(session)
            user = await db.get_user(user_id)
            if user:
                last_open = user.last_open

                if last_open.tzinfo is None:
                    # Предполагаем UTC для записей без timezone
                    last_open = last_open.replace(tzinfo=timezone.utc)

                hour = 2 if datetime.now(timezone.utc).weekday() >= 5 else 3

                if last_open + timedelta(hours=hour) <= datetime.now(timezone.utc):
                    card = await random_card( user.pity)
                    text = await Text().card_formatter(card, user)
                    await message.reply_photo(FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)
                    if card not in user.inventory:
                        user.inventory.append(card)
                    match user.pity:
                        case _ if user.pity <= 0:
                            user.pity = 100
                        case _:
                            user.pity -= 1
                    user.last_open = datetime.now(timezone.utc)
                    user.yens += card.value + (math.ceil(card.value * 0.1) if user.vip else 0)
                    await session.commit()
                else:
                    text = await Text().nottime(user.last_open)
                    if text is None:
                        messages = Text._load_messages()
                        text = messages["not_enough_time"]
                    await message.reply(text)
            else:
                messages = Text._load_messages()
                await message.reply(messages["not_registered"])
        finally:
            # Убираем пользователя из списка после завершения (даже если была ошибка)
            if user_id in user_card_opens:
                user_card_opens.remove(user_id)
    else:
        await message.reply("⏳ Подождите, карта уже открывается!")

@router.message(Command("profile"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        place_on_top = await db.get_user_place_on_top(user)
        text = await Text().profile_creator(user.clan_member.clan if user.clan_member else None,user.profile,place_on_top, session)
        profile_photo = await user_photo_link(message)
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        text = await Text().not_user(message.from_user.full_name)
        await message.reply(text)

@router.message(Command("daily"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    messages = Text._load_messages()
    try:
        # Получаем ID текущей ежедневной вселенной из Redis
        verse_id = await RedisRequests.daily_verse()

        if verse_id:
            # Получаем информацию о вселенной из базы данных
            db = DB(session)
            verse = await db.get_verse(verse_id)

            if verse:
                # Форматируем сообщение с информацией о ежедневной вселенной
                text = messages["daily_verse"] % verse.name
                await message.reply(text)
            else:
                await message.reply(messages["daily_verse_error"])
        else:
            await message.reply(messages["daily_verse_error"])
    except Exception as e:
        logger.error(f"Ошибка при получении ежедневной вселенной: {str(e)}", exc_info=True)
        await message.reply(messages["daily_verse_error"])
