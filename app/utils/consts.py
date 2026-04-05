from datetime import timezone, timedelta

RARITIES = [1, 2, 3, 4, 5]
CHANCES = [55, 27, 12, 4.5, 1]
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