from datetime import timezone, timedelta

from kubiks import load
from app.utils.enums.shop import ShopEnum


CONFIG = load("app/utils/constants.kbk")

SHOP_ITEMS = {
    "f": ShopEnum.FREE_OPEN,
    "b": ShopEnum.BOOST,
    "a": ShopEnum.ADD_PITY,
    "y": ShopEnum.YENS_BOOST,
    "r": ShopEnum.RANDOM_HRONO,
}

SHINY_CHANCE = CONFIG["shiny_chance"]
DAILY_VERSE_BOOST = CONFIG["daily_verse_boost"]
DAILY_VERSE_YEN_BOOST = CONFIG["daily_verse_yen_boost"]

SEASON_ROLL_COST = CONFIG["season_roll_cost"]
COOLDOWN = CONFIG["cooldown"]
CLAN_CREATION_COST = CONFIG["clan_creation_cost"]

PLAYERS_IN_TOP = CONFIG['players_in_top']

DAILY_VERSE_TTL = 24 * 60 * 60
BOOST_TTL = 3 * 24 * 60 * 60

MSK_TIMEZONE = timezone(
    timedelta(hours=CONFIG["offset"])
)

RARITY_VALUE_RANGES = {
    rarity: tuple(values)
    for rarity, values in CONFIG["rarity_value_ranges"].items()
}

RARITY_EMOJIES = {
    "C": "<tg-emoji emoji-id='5253937676771435025'>🔵</tg-emoji>",
    "B": "<tg-emoji emoji-id='5255760684230155919'>🟢</tg-emoji>",
    "SR": "<tg-emoji emoji-id='5251321096795363331'>🟡</tg-emoji>",
    "S": "<tg-emoji emoji-id='5251605354910883000'>🟠</tg-emoji>",
    "SSR": "<tg-emoji emoji-id='5251610727914972054'>🔴</tg-emoji>",
    "Лимитированный": "🟣",
}

SLOT_RARITY_MAP = {
    "Обычный": "common",
    "Редкий": "uncommon",
    "Мифический": "mythic",
    "Легендарный": "legend",
    "Хроно": "hrono",
}