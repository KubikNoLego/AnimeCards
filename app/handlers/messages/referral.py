import os

from aiogram import Router,F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.messages import MText
from app.func import create_qr
from db import DB


router = Router()


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

        stats_message = MText.get("refferal_text").format(
            link=referral_link,
            referral=len(user.referrals),
            total=total_reward,
            award="50 до 150" if not user.vip else "100 до 150")
        try:
            qr_file = await create_qr(referral_link)
            try:
                await message.reply_photo(qr_file, caption=stats_message,
                                        parse_mode="HTML")
            finally:
                # Удаляем временный файл в любом случае
                if hasattr(qr_file, 'path') and os.path.exists(qr_file.path):
                    os.unlink(qr_file.path)
        except Exception as e:
            await message.reply(MText.get("qr_error"))
    else:
        await message.reply(MText.get("qr_error"))