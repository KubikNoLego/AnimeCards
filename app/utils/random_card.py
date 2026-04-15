import random

from app.database.models import Card
from app.utils.consts import CHANCES, RARITIES


def soft_pity(pity: int) -> float:
    base = 0.01
    soft_start = 75
    max_pity = 100

    if pity >= max_pity:
        return 1.0

    if pity < soft_start:
        return base

    x = (pity - soft_start) / (max_pity - soft_start)
    return base + (1 - base) * (x ** 2)

def roll_rarity(pity: int, boost: bool) -> int:
    if pity >= 100:
        return 5

    chances = CHANCES.copy()

    if boost:
        chances[0] *= 1.1
        chances[1] *= 0.5
        chances[2] *= 1.5
        chances[3] *= 2.0
        chances[4] *= 2.5

        total = sum(chances)
        chances = [c / total for c in chances]

    hrono_chance = soft_pity(pity)

    if boost:
        hrono_chance *= 2.5

    other_sum = sum(chances[:-1])
    scale = (1 - hrono_chance) / other_sum

    scaled = [c * scale for c in chances[:-1]] + [hrono_chance]

    return random.choices(RARITIES, scaled, k=1)[0]

def choose_card(cards: list[Card],
                    daily_verse: None | int = None) -> Card:
    weights = []
    
    for card in cards:
        w = 1
        if daily_verse and daily_verse == card.verse.id: w*=1.25
        
        weights.append(w)

    return random.choices(cards,weights,k=1)[0]