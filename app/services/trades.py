

from datetime import datetime, timedelta

from app.database.requests import DB
from app.utils.constants import MSK_TIMEZONE
from app.utils.enums.trades_enums import TradeEnum


async def check_trade_request(db: DB, trader_id: int, 
                            current_user_id: int) -> TradeEnum:
    if not trader_id:
        return TradeEnum.NOT_USER

    if trader_id == current_user_id:
        return TradeEnum.CANT_TRADE_WITH_SELF

    trader = await db.user.get_user(trader_id)
    if not trader:
        return TradeEnum.NOT_USER

    trade = await db.trade.get_trade(trader_id)
    if not trade:
        return TradeEnum.TRADE_NOT_FOUND

    # Проверяем, не заблокирован ли трейд другим партнером
    if (trade.partner_id and trade.partner_id != current_user_id and
        trade.partner_added_at + timedelta(minutes=10) >= datetime.now(MSK_TIMEZONE)):
        return TradeEnum.USER_ALREADY_TRADING

    card = await db.card.get_card(trade.card_id)
    if not card:
        return TradeEnum.CARD_NOT_FOUND

    return TradeEnum.SUCCESS

async def add_partner_to_trade(db: DB, trade, user_id: int) -> None:
    trade.partner_id = user_id
    trade.partner_card = None
    trade.partner_added_at = datetime.now(MSK_TIMEZONE).replace(tzinfo=None)
    await db.session.commit()