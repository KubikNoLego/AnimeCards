import random

from app.database.models import Card
from app.utils.consts import CHANCES, RARITIES


def soft_pity(pity: int) -> float:
    MAX_PITY = 100
    base_chance = 0.01
    soft_start = 25
    rpity = 100-pity

    if rpity > soft_start:
        chance = (rpity - soft_start) / (MAX_PITY - soft_start)
        return base_chance + chance * (1 - base_chance)

    return base_chance

def roll_rarity(pity: int) -> int:
    if pity == 0:
        return 5
    
    chances = CHANCES.copy()

    hrono_chance = soft_pity(pity)

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