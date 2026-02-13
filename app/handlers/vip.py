# Стандартные библиотеки
from datetime import datetime, timedelta, timezone, timedelta

# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Сторонние библиотеки
from aiogram import Router,F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


# Локальные импорты
from app.filters import Private
from db import VipSubscription, DB
from app.messages import MText

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

        # Создаем инлайн-клавиатуру с кнопкой покупки
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Купить VIP за 150 ⭐", callback_data="buy_vip")
        builder.adjust(1)

        # Отправляем сообщение с предложением VIP
        await message.answer(vip_message, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на покупку VIP: {e}")
        await message.answer(MText.get("processing_request_error"))

@router.callback_query(F.data == "buy_vip")
async def buy_vip(callback: CallbackQuery, session: AsyncSession):
    user = await DB(session).get_user(callback.from_user.id)

    if not user:
        await callback.message.answer(MText.get("user_not_found_vip"))
        return

    if user.vip:
        await callback.message.answer(MText.get("vip_already_active"))
        return


    try:
        vip_price_stars = 150

        await callback.message.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="💎 VIP",
            description="Получите эксклюзивные преимущества: увеличенные награды, больше бонусов за рефералов, полный доступ к магазину и специальный символ 👑 в профиле!",
            payload=f"vip_subscription_{user.id}",
            currency="XTR",
            prices=[LabeledPrice(label="VIP Подписка", amount=vip_price_stars)],
            is_flexible=False)

    except Exception as e:
        logger.error(f"Ошибка при отправке invoice для VIP подписки: {e}")
        await callback.message.answer(MText.get("invoice_error"))


@router.callback_query(F.data == "cancel_vip_purchase")
async def cancel_vip_purchase(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены покупки VIP подписки."""
    try:
        await state.clear()
        await callback.message.answer(MText.get("purchase_cancelled"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при отмене покупки VIP: {e}")
        await callback.answer(MText.get("cancel_error"), show_alert=True)

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработчик PreCheckoutQuery - подтверждение оплаты."""
    try:
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        logger.error(f"Ошибка при обработке PreCheckoutQuery: {e}")
        await pre_checkout_query.answer(ok=False, error_message=MText.get("processing_error"))

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик успешной оплаты - создание VIP подписки."""
    try:
        
        # Получаем пользователя
        user = await DB(session).get_user(message.from_user.id)

        if not user:
            await message.answer(MText.get("user_not_found_vip"))
            await state.clear()
            return

        # Проверяем, есть ли уже VIP подписка
        if user.vip:
            await message.answer(MText.get("vip_already_active"))
            await state.clear()
            return

        # Создаем VIP подписку навсегда (100 лет)
        start_date = datetime.now(MSK_TIMEZONE)
        end_date = start_date + timedelta(days=36500)

        new_vip = VipSubscription(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date
        )

        session.add(new_vip)

        user.free_open += 4

        await session.commit()

        # Сбрасываем состояние
        await state.clear()

        # Сообщаем об успешной покупке
        await message.answer(MText.get("vip_purchase_success"))

    except Exception as e:
        logger.error(f"Ошибка при обработке успешной оплаты VIP: {e}")
        await message.answer(MText.get("payment_error"))
        await state.clear()