from datetime import datetime, timedelta
import random
from html import escape

from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.types import FSInputFile, Message
from aiogram.filters import CommandStart,CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.filters import Private
from app.func.consts import MSK_TIMEZONE
from app.keyboards import main_kb, trade_kb_pagination
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

            case "t":
                trader = await db.get_user(int(value))

                if not trader:
                    await message.answer(MText.get("user_not_found_short"))
                    return

                if trader.id == user.id:
                    await message.answer(MText.get("u_cant_trade_with_self"))
                    return

                trade = await db.get_trade(trader.id)
                
                if not trade:
                    await message.answer(MText.get("user_not_found_short"))
                    return

                if (trade.partner_id and trade.partner_id != user.id and 
            trade.partner_added_at + timedelta(minutes=10) >= datetime.now()):
                    
                    await message.answer(MText.get("user_already_trading"))
                    return


                card = await db.get_card(trade.card_id)

                if not card:
                    await message.answer(MText.get("user_not_found_short"))
                    return

                card_info = MText.get("card").format(name=card.name,
                                                    verse=card.verse_name,
                                                    rarity=card.rarity_name,
                                                    value=card.value)
                card_info = card_info + ("\n\n✨ Shiny" if card.shiny else "")

                await message.answer_photo(FSInputFile(
                    path=f"app/icons/{card.verse.name}/{card.icon}"),
                    caption=card_info, reply_markup=await trade_kb_pagination())
                
                trade.partner_id = user.id
                trade.partner_card = None
                trade.partner_added_at = datetime.now(MSK_TIMEZONE).replace(tzinfo=None)

                await session.commit()

                return

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

                referrer_link = f'<a href="tg://user?id={inviter.id}">{escape(inviter.name)}</a>'
                new_user_link = f'<a href="tg://user?id={user.id}">{escape(user.name)}</a>'

                await message.reply(MText.get("referral_welcome").format(referrer_link=referrer_link))

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
                    logger.error(f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")

    message_text = MText.get("start")
    keyboard = await main_kb()
    await state.clear()
    await message.reply(message_text, reply_markup=keyboard, disable_web_page_preview=True)