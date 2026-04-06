from enum import Enum

class TradeEnum(Enum):
    NOT_USER = "user_not_found_short"
    CANT_TRADE_WITH_SELF = "u_cant_trade_with_self"
    USER_ALREADY_TRADING = "user_already_trading"
    TRADE_NOT_FOUND = "user_not_found_short"
    CARD_NOT_FOUND = "user_not_found_short"
    SUCCESS = 'success'