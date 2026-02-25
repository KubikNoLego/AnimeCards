from datetime import datetime, timedelta

from aiogram import Router,F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.messages import MText
from app.keyboards import vip_kb
from app.func import MSK_TIMEZONE
from app.filters import Private
from db import DB


router = Router()


@router.message(F.text == "💎 Купить VIP", Private())
async def vip_offer_handler(message: Message, session: AsyncSession):
    """Обработчик кнопки покупки VIP подписки."""
    try:

        # Получаем пользователя из базы данных
        user = await DB(session).get_user(message.from_user.id)

        if not user:
            await message.answer(MText.get("user_not_found_vip"))
            return

        # Проверяем, есть ли у пользователя VIP подписка
        if user.vip:
            current_time = datetime.now(MSK_TIMEZONE)

            # Если подписка истекла, удаляем ее
            if user.vip.end_date <= current_time:
                await DB(session).delete_vip_subscription(user.id)
                user.vip = None  # Обновляем объект пользователя
            else:
                # Если подписка еще активна, сообщаем пользователю
                await message.answer(MText.get("vip_already_active"))
                return

        # Загружаем сообщение о VIP предложении
        vip_message = MText.get("vip_offer")

        builder = await vip_kb()

        # Отправляем сообщение с предложением VIP
        await message.answer(vip_message, reply_markup=builder)

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на покупку VIP: {e}")
        await message.answer(MText.get("processing_request_error"))