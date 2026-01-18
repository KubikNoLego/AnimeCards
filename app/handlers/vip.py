# Стандартные библиотеки
from datetime import datetime, timedelta, timezone
import json

# Сторонние библиотеки
from aiogram import Router,F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import validate_email

# Локальные импорты
from app.filters import Private
from app.func import _load_messages
from db.models import User, VipSubscription
from db.requests import get_user
from configR import config

def validate_email(email: str) -> bool:
    """Проверка валидности email адреса."""
    return validate_email.validate_email(email)


class PushareState(StatesGroup):
    email: State

router = Router()

@router.message(F.text == "💎 Купить VIP", Private())
async def vip_offer_handler(message: Message, session: AsyncSession):
    """Обработчик кнопки покупки VIP подписки."""
    try:
        # logger.info(f"Обработка запроса на покупку VIP для пользователя {message.from_user.id}")

        # Загружаем сообщения в начале функции
        messages = _load_messages()

        # Получаем пользователя из базы данных
        user = await get_user(session, message.from_user.id)

        if not user:
            await message.answer(messages["user_not_found_vip"])
            return

        # Проверяем, есть ли у пользователя VIP подписка
        if user.vip:
            current_time = datetime.now(timezone.utc)

            # Если подписка истекла, удаляем ее
            if user.vip.end_date <= current_time:
                # logger.info(f"Удаляем истекшую VIP подписку для пользователя {user.id}")
                await session.execute(delete(VipSubscription).where(VipSubscription.user_id == user.id))
                await session.commit()
                user.vip = None  # Обновляем объект пользователя
            else:
                # Если подписка еще активна, сообщаем пользователю
                end_date = user.vip.end_date.astimezone(timezone.utc)
                await message.answer(messages["vip_already_active"].format(end_date=end_date.strftime('%d.%m.%Y %H:%M')))
                return

        # Загружаем сообщение о VIP предложении
        vip_message = messages["vip_offer"]

        # Создаем инлайн-клавиатуру с кнопкой покупки
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Купить VIP за 299 ₽", callback_data="buy_vip")
        builder.adjust(1)

        # Отправляем сообщение с предложением VIP
        await message.answer(vip_message, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на покупку VIP: {e}")
        await message.answer(messages["processing_request_error"])

@router.callback_query(F.data == "buy_vip")
async def buy_vip(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    messages = _load_messages()

    if not user:
        await callback.message.answer(messages["user_not_found_vip"])
        return

    if user.vip:
        end_date = user.vip.end_date.astimezone(timezone.utc)
        await callback.message.answer(messages["vip_already_active"].format(end_date=end_date.strftime('%d.%m.%Y %H:%M')))
        return


    # Отправляем invoice для оплаты
    try:
        # Пробуем без provider_data для диагностики проблемы
        vip_price_rub = 299.00  # Цена в рублях

        await callback.message.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="💎 VIP Подписка на 30 дней",
            description="Получите эксклюзивные преимущества: увеличенные награды, больше бонусов за рефералов, полный доступ к магазину и специальный символ 👑 в профиле!",
            payload=f"vip_subscription_{user.id}",
            provider_token=config.PAYMENT_PROVIDER.get_secret_value(),
            currency="RUB",
            prices=[LabeledPrice(label="VIP Подписка", amount=int(vip_price_rub * 100))],  # Цена в копейках для Telegram
            need_email=True,
            send_email_to_provider=True,
            is_flexible=False,
        provider_data=json.dumps({"receipt": {
        "items": [
          {
            "description": "Подписка VIP на месяц",
            "quantity": "1.00",
            "amount": {
              "value": f"{vip_price_rub:.2f}",
              "currency": "RUB"
            },
            "vat_code": 1}]}}))


    except Exception as e:
        logger.error(f"Ошибка при отправке invoice для VIP подписки: {e}")
        await callback.message.answer(messages["invoice_error"])


@router.callback_query(F.data == "cancel_vip_purchase")
async def cancel_vip_purchase(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены покупки VIP подписки."""
    messages = _load_messages()
    try:
        await state.clear()
        await callback.message.answer(messages["purchase_cancelled"])
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при отмене покупки VIP: {e}")
        await callback.answer(messages["cancel_error"], show_alert=True)

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработчик PreCheckoutQuery - подтверждение оплаты."""
    messages = _load_messages()
    try:
        # logger.info(f"PreCheckoutQuery от пользователя {pre_checkout_query.from_user.id}")
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        logger.error(f"Ошибка при обработке PreCheckoutQuery: {e}")
        await pre_checkout_query.answer(ok=False, error_message=messages["processing_error"])

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик успешной оплаты - создание VIP подписки."""
    messages = _load_messages()
    try:
        # logger.info(f"Успешная оплата от пользователя {message.from_user.id}")

        # Получаем email из successful_payment (Telegram запросил его во время оплаты)
        email = message.successful_payment.order_info.email
        if not email:
            logger.error(f"Email не найден в successful_payment для пользователя {message.from_user.id}")
            await message.answer(messages["payment_error_no_email"])
            await state.clear()
            return

        # Получаем пользователя
        user = await get_user(session, message.from_user.id)

        if not user:
            await message.answer(messages["user_not_found_vip"])
            await state.clear()
            return

        # Проверяем, есть ли уже VIP подписка
        if user.vip:
            end_date = user.vip.end_date.astimezone(timezone.utc)
            await message.answer(messages["vip_already_active"].format(end_date=end_date.strftime('%d.%m.%Y %H:%M')))
            await state.clear()
            return

        # Создаем VIP подписку на 30 дней
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=30)

        new_vip = VipSubscription(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            email=email
        )

        session.add(new_vip)
        await session.commit()

        # Сбрасываем состояние
        await state.clear()

        # Сообщаем об успешной покупке
        await message.answer(messages["vip_purchase_success"].format(end_date=end_date.strftime('%d.%m.%Y %H:%M')))

    except Exception as e:
        logger.error(f"Ошибка при обработке успешной оплаты VIP: {e}")
        await message.answer(messages["payment_error"])
        await state.clear()
        # Сбрасываем состояние
