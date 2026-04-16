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

RARITIES = [1, 2, 3, 4, 5]
CHANCES = [.55, .27, .12, .045, .01]
SHINY_CHANCE = 0.05
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
            "Обычный": "🔵",
            "Редкий": "🟢",
            "Легендарный": "🟡",
            "Мифический": "🟠",
            "Хроно": "🔴",
            "Лимитированный": "🟣"
}
SLOT_RARITY_MAP = {
    "Обычный": "common",
    "Редкий": "uncommon",
    "Мифический": "mythic",
    "Легендарный": "legend",
    "Хроно": "hrono",
}