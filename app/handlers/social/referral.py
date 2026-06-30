import os

from aiogram import Router,F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.messages import MText
from app.services.profile import create_qr
from app.database import DB


router = Router()


@router.callback_query(F.data == "referral_link")
async def _(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки реферальной ссылки."""
    db = DB(session)
    user = await db.user.get_user(callback.from_user.id)
    if user:
        total_reward = sum(referral.reward for referral in user.referrals)
        awarded = sum(referral.reward for referral in user.referrals if referral.claimed)
        bot_info = await callback.bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start=r_{user.id}"

        stats_message = MText.get("refferal_text").format(
            link=referral_link,
            referral=len(user.referrals),
            awarded = awarded,
            total=total_reward)
        try:
            qr_file = await create_qr(referral_link)
            try:
                await callback.message.answer_photo(qr_file, caption=stats_message,
                                        parse_mode="HTML")
            finally:
                if hasattr(qr_file, 'path') and os.path.exists(qr_file.path):
                    os.unlink(qr_file.path)
        except Exception as e:
            await callback.message.answer(MText.get("qr_error"))
    else:
        await callback.message.answer(MText.get("qr_error"))

    await callback.message.delete()