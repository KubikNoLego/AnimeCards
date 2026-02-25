import random
from html import escape

from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart,CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.filters import Private
from app.keyboards import main_kb
from app.messages import MText
from db import DB


router = Router()

@router.message(CommandStart(),Private())
async def _(message: Message, command: CommandObject,session: AsyncSession,
            state: FSMContext):
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
                
                # Вычисляем награду до создания реферала
                reward_amount = (random.randint(50, 150) 
                                if not inviter.vip
                                else random.randint(100, 150))

                # Добавляем реферальную связь с указанием награды
                referral = await db.add_referral(referral_id=user.id,
                                                referrer_id=inviter_id,
                                                referrer_reward=reward_amount)
                if not referral:
                    await message.answer(MText.get("sorry"))
                    return

                # Награждаем реферрера за реферала
                await db.get_award(inviter_id, reward_amount)
                
                # Обновляем данные инвайтера для получения актуального баланса
                inviter = await db.get_user(inviter_id)
                
                referrer_link = f'<a href="tg://user?id={inviter.id}">{
                    escape(inviter.name)}</a>'
                new_user_link = f'<a href="tg://user?id={user.id}">{
                    escape(user.name)}</a>'

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
                                yens=inviter.balance)
                            )
                except Exception as e:
                    logger.error(
                f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")

    message_text = MText.get("start")
    keyboard = await main_kb()
    await state.clear()
    await message.reply(message_text, reply_markup=keyboard,
                        disable_web_page_preview=True)
