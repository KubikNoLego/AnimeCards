from datetime import timezone, timedelta

from app.utils.enums.shop import ShopEnum


SHOP_ITEMS = {
    'f': ShopEnum.FREE_OPEN,
    'b': ShopEnum.BOOST,
    'a': ShopEnum.ADD_PITY,
    'y': ShopEnum.YENS_BOOST,
    'r': ShopEnum.RANDOM_HRONO
}

DAILY_VERSE_TTL = 24 * 60 * 60
BOOST_TTL = 3 * 24 * 60 * 60

SHINY_CHANCE = 1
DAILY_VERSE_BOOST = 4
DAILY_VERSE_YEN_BOOST = .2
SEASON_ROLL_COST = 30
MSK_TIMEZONE = timezone(timedelta(hours=3))
COOLDOWN = 3
RARITY_VALUE_RANGES = {
    "Обычный": (1, 5),
    "Редкий": (5, 20),
    "Мифический": (20, 50),
    "Легендарный": (40, 80),
    "Хроно": (100, 200),
    "Лимитированный": (0, 0)
}
RARITY_EMOJIES = {
            "C": "<tg-emoji emoji-id='5253937676771435025'>🔵</tg-emoji>",
            "B": "<tg-emoji emoji-id='5255760684230155919'>🟢</tg-emoji>",
            "SR": "<tg-emoji emoji-id='5251321096795363331'>🟡</tg-emoji>",
            "S": "<tg-emoji emoji-id='5251605354910883000'>🟠</tg-emoji>",
            "SSR": "<tg-emoji emoji-id='5251610727914972054'>🔴</tg-emoji>",
            "Лимитированный": "🟣"
}
SLOT_RARITY_MAP = {
    "Обычный": "common",
    "Редкий": "uncommon",
    "Мифический": "mythic",
    "Легендарный": "legend",
    "Хроно": "hrono",
}

CLAN_CREATION_COST = 500