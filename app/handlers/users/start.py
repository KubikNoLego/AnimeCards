from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.types import InputRichMessage, Message
from aiogram.filters import CommandStart,CommandObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.services.ReferralService import ReferralService
from app.keyboards import main_kb
from app.messages import MText
from app.database import DB
from app.utils.trades_utils import send_trade_card
from app.services.trades import add_partner_to_trade, check_trade_request
from app.utils.enums.trades_enums import TradeEnum


router = Router()

@router.message(CommandStart(),Private())
async def _(message: Message, command: CommandObject, session: AsyncSession,
            state: FSMContext):
    user = await message.bot.get_chat(message.from_user.id)

    db = DB(session)
    user, created = await db.user.create_or_update_user(user.id,
                                message.from_user.username,
                                user.full_name)
    
    if user is None:
        await message.answer("Произошла ошибка при регистрации. Попробуйте позже.")
        return

    if command.args:
        option,value = command.args.split("_")
        match option:

            case "t":
                try:
                    trader_id = int(value)
                except:
                    trader_id = None

                if (enum := await check_trade_request(db, trader_id, 
                                            user.id)) != TradeEnum.SUCCESS:
                    await message.answer(MText.get(enum.value))
                    return

                trade = await db.trade.get_trade(trader_id)
                card = await db.card.get_card(trade.card_id)

                await send_trade_card(message, card)
                await add_partner_to_trade(db, trade, user.id)

                return

            case "r":
                try:
                    referrer_id = int(value)
                except:
                    await message.answer(MText.get("not_user_id"))
                    return
                
                await ReferralService.add_referral(referrer_id,
                                            message.from_user.id,
                                            created,
                                            message,
                                            session)

    keyboard = await main_kb()
    await state.clear()
    await message.answer_rich(InputRichMessage(html=MText.get("start")), reply_markup=keyboard, disable_web_page_preview=True)