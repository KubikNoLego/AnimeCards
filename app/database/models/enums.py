from enum import Enum


class CardType(Enum):
    STANDARD = "Стандартная"
    SEASONAL = "Сезонная"

class ShopItems(Enum):
    STANDARD_SPIN = "standard_spin"
    LUCK_BOOST = "luck_boost"
    YEN_BOOST = "yen_boost"
    MYSTERY_BOX = "mystery_box"
    DUPLICATOR = "duplicator"