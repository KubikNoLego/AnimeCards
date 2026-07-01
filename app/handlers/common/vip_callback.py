from datetime import datetime, timedelta, timedelta

from aiogram import Router,F
from aiogram.types import Message, CallbackQuery, LabeledPrice,PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import UserTitle
from app.keyboards.inline.datas import VipPurchase
from app.utils.constants import MSK_TIMEZONE, VIP_PRICE
from app.messages import MText
from app.database import VipSubscription, DB


router = Router()

from aiogram.types import LabeledPrice

@router.callback_query(VipPurchase.filter())
async def buy_vip(callback: CallbackQuery, callback_data: VipPurchase):
    if callback_data.months == 1:
        title = "VIP на 1 месяц"
        stars = 40

    elif callback_data.months == 6:
        title = "VIP на 6 месяцев"
        stars = 150

    else:
        title = "VIP навсегда"
        stars = 350

    await callback.message.answer_invoice(
        title=title,
        description="Покупка VIP",
        payload=f"vip:{callback_data.months}",
        currency="XTR",
        prices=[
            LabeledPrice(
                label=title,
                amount=stars
            )
        ]
    )

@router.pre_checkout_query()
async def pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message, session: AsyncSession):
    payload = message.successful_payment.invoice_payload

    _, months = payload.split(":")
    months = int(months)

    user = await DB(session).user.get_user(message.from_user.id)

    days = 30 * months

    if user.vip:
        user.vip.end_date += timedelta(days=days)
    else:
        now = datetime.now(MSK_TIMEZONE)
        user.vip = VipSubscription(
            user_id=user.id,
            start_date=now,
            end_date=now + timedelta(days=days),
        )
        user_title = UserTitle(user_id=user.id,
                            title_id=21,
                            obtained_at=now)
        user.profile.title_id = 21
        session.add(user_title)

    await session.commit()

    await message.answer("🎉 Спасибо за покупку!")