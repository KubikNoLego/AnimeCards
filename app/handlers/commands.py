from datetime import datetime, timedelta, timezone
import random
from aiogram import Router,F
from aiogram.filters import CommandStart,CommandObject,Command
from aiogram.types import Message,FSInputFile
from aiogram.utils.markdown import html_decoration


from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.filters import Private
from app.func import user_photo_link, start_message_generator
from app.func.utils import _load_messages, card_formatter, not_user, nottime, profile_creator,random_card
from app.keyboards import main_kb
from db.models import Referrals, User, Verse
from db.requests import create_or_update_user, get_award, get_user_place_on_top, add_referral, RedisRequests

router = Router()

@router.message(CommandStart(),Private())
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user = await message.bot.get_chat(message.from_user.id)
    
    
    await create_or_update_user(user.id,
                                message.from_user.username,
                                user.full_name,
                                user.bio,
                                session
                            )
    user = await session.scalar(select(User).filter_by(id=user.id))

    if command.args:
        option,value = command.args.split("_")
        match option:
            case "r":
                try:
                    inviter_id = int(value)
                except:
                    inviter_id = None

                if inviter_id:
                    inviter = await session.scalar(select(User).filter_by(id=inviter_id))
                    if inviter:
                        # Добавляем реферальную связь
                        referral = await add_referral(session, referral_id=user.id, referrer_id=inviter_id)
                        if referral:
                            logger.info(f"Добавлен реферал: {inviter_id} -> {user.id}")

                            # Случайная награда от 100 до 700 йен
                            reward_amount = random.randint(100, 700)

                            # Награждаем реферрера за реферала
                            reward_success = await get_award(session,inviter_id,reward_amount)
                            if reward_success:
                                logger.info(f"Пользователь {inviter_id} получил {reward_amount} йен за реферала")

                                # Создаем кликабельную ссылку на профиль реферрера
                                referrer_link = f'<a href="tg://user?id={inviter.id}">{html_decoration.quote(inviter.name)}</a>'

                                # Создаем кликабельную ссылку на профиль нового пользователя
                                new_user_link = f'<a href="tg://user?id={user.id}">{html_decoration.quote(user.name)}</a>'

                                await message.reply(f"🎉 Вы были приглашены пользователем {referrer_link}!")

                                # Отправляем сообщение реферреру о новом реферале
                                try:
                                    # Получаем текущий баланс реферрера для отображения общего количества йен
                                    updated_inviter = await session.scalar(select(User).filter_by(id=inviter_id))
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

                                await message.reply(f"💰 {referrer_link} получил {reward_amount} ¥ за ваше приглашение!")
                            else:
                                logger.info(f"Пользователь {inviter_id} уже получил награду за этого реферала")

                                # Создаем кликабельную ссылку на профиль реферрера
                                referrer_link = f'<a href="tg://user?id={inviter.id}">{html_decoration.quote(inviter.name)}</a>'

                                # Создаем кликабельную ссылку на профиль нового пользователя
                                new_user_link = f'<a href="tg://user?id={user.id}">{html_decoration.quote(user.name)}</a>'

                                await message.reply(f"🎉 Вы были приглашены пользователем {referrer_link}!")

                                # Отправляем сообщение реферреру о новом реферале (даже если награда уже была выдана)
                                try:
                                    await message.bot.send_message(
                                        inviter.id,
                                        f"🎉 Новый реферал! {new_user_link} использовал вашу реферальную ссылку!"
                                    )
                                except Exception as e:
                                    logger.error(f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")

                                await message.reply(f"💰 {referrer_link} уже получил бонус за ваше приглашение.")


    message_text = await start_message_generator(user.start)
    await message.reply(message_text, reply_markup=await main_kb())


@router.message(Command("card"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user = await session.scalar(select(User).filter_by(id=message.from_user.id).with_for_update())
    if user:
        last_open = user.last_open
        
        if last_open.tzinfo is None:
            # Предполагаем UTC для записей без timezone
            last_open = last_open.replace(tzinfo=timezone.utc)

        hour = 2 if datetime.now(timezone.utc).weekday() >= 5 else 3

        if last_open + timedelta(hours=hour) <= datetime.now(timezone.utc):
            card = await random_card(session, user.pity)
            text = await card_formatter(card)
            await message.reply_photo(FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)
            if card not in user.inventory:
                user.inventory.append(card)
            match user.pity:
                case _ if user.pity <= 0:
                    user.pity = 100
                case _:
                    user.pity -= 1
            user.last_open = datetime.now(timezone.utc)
            user.yens += card.value
            await session.commit()
        else:
            text = await nottime(user.last_open)
            if text is None:
                text = "<i>⏳ До следующего открытия осталось немного времени</i>"
            await message.reply(text)
    else:
        messages = _load_messages()
        await message.reply(messages["not_registered"])

@router.message(Command("profile"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user = await session.scalar(select(User).filter_by(
                                                    id=message.from_user.id))
    if user:
        place_on_top = await get_user_place_on_top(session,user)
        text = await profile_creator(user.profile,place_on_top, session)
        profile_photo = await user_photo_link(message)
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        text = await not_user(message.from_user.full_name)
        await message.reply(text)

@router.message(Command("daily"))
async def _(message: Message, command: CommandObject,session: AsyncSession):
    messages = _load_messages()
    try:
        # Получаем ID текущей ежедневной вселенной из Redis
        verse_id = await RedisRequests.daily_verse()

        if verse_id:
            # Получаем информацию о вселенной из базы данных
            verse = await session.scalar(select(Verse).filter_by(id=verse_id))

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
