from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from html import escape as html_escape

from app.messages.MessageControl import MText

from ..database.models import Card, BattleInventory, Verse, User
from .consts import RARITY_EMOJIES, SLOT_RARITY_MAP, RARITY_VALUE_RANGES

# Слоты для сравнения
SLOTS = ["common", "uncommon", "mythic", "legend", "hrono"]
SLOT_NAMES = {
    "common": "Обычный",
    "uncommon": "Редкий", 
    "mythic": "Мифический",
    "legend": "Легендарный",
    "hrono": "Хроно"
}

@dataclass
class SlotResult:
    """Результат сравнения в одном слоте."""
    slot: str
    user1_card: Optional[Card]
    user2_card: Optional[Card]
    user1_value: int
    user2_value: int
    winner: int  # 0 - ничья, 1 - первый игрок, 2 - второй игрок

@dataclass  
class BattleResult:
    """Результат боя между двумя колодами."""
    user1_wins: int  # Количество побед по слотам
    user2_wins: int  # Количество побед по слотам
    draws: int       # Количество ничьих
    slot_results: List[SlotResult]
    overall_winner: int  # 0 - ничья, 1 - первый игрок, 2 - второй игрок
    
    @property
    def user1_name(self) -> str:
        return "Игрок 1"
    
    @property
    def user2_name(self) -> str:
        return "Игрок 2"

async def get_card_value(card: Card, battle_inv: BattleInventory):
    if card.rarity_name != "Лимитированный":
        return card.value
    
    for rarity, slot in SLOT_RARITY_MAP.items():
        slot_inv = getattr(battle_inv, slot, None)
        if slot_inv and slot_inv.id == card.id:
            return RARITY_VALUE_RANGES[rarity][1]
        
def get_card_value_for_battle(card: Card, battle_inv: BattleInventory) -> int:
    """
    Получить стоимость карты для боя.
    Для лимитированных карт используется максимальное значение редкости слота.
    """
    if card.rarity_name != "Лимитированный":
        return card.value
    
    # Для лимитированной карты определяем слот и возвращаем максимальное значение
    for rarity, slot in SLOT_RARITY_MAP.items():
        slot_card = getattr(battle_inv, slot, None)
        if slot_card and slot_card.id == card.id:
            return RARITY_VALUE_RANGES[rarity][1]
    
    return card.value

def calculate_deck_value(battle_inv: BattleInventory) -> int:
    """
    Вычислить общую стоимость колоды.
    """
    total = 0
    for card in battle_inv.cards:
        total += get_card_value_for_battle(card, battle_inv)
    return total

def compare_cards(card1: Optional[Card], card2: Optional[Card], 
                battle_inv1: BattleInventory, battle_inv2: BattleInventory) -> int:
    """
    Сравнить две карты. Возвращает:
    1 - первая карта побеждает
    2 - вторая карта побеждает  
    0 - ничья
    """
    if card1 is None and card2 is None:
        return 0
    if card1 is None:
        return 2
    if card2 is None:
        return 1
    
    value1 = get_card_value_for_battle(card1, battle_inv1)
    value2 = get_card_value_for_battle(card2, battle_inv2)
    
    if value1 > value2:
        return 1
    elif value2 > value1:
        return 2
    return 0

async def battle_decks(battle_inv1: BattleInventory, battle_inv2: BattleInventory) -> BattleResult:
    """
    Провести бой между двумя колодами.
    Сравниваются карты по слотам, побеждает тот, у кого больше побед по слотам.
    """
    slot_results = []
    user1_wins = 0
    user2_wins = 0
    draws = 0
    
    for slot in SLOTS:
        card1 = getattr(battle_inv1, slot, None)
        card2 = getattr(battle_inv2, slot, None)
        
        value1 = get_card_value_for_battle(card1, battle_inv1) if card1 else 0
        value2 = get_card_value_for_battle(card2, battle_inv2) if card2 else 0
        
        winner = compare_cards(card1, card2, battle_inv1, battle_inv2)
        
        if winner == 1:
            user1_wins += 1
        elif winner == 2:
            user2_wins += 1
        else:
            draws += 1
        
        slot_results.append(SlotResult(
            slot=slot,
            user1_card=card1,
            user2_card=card2,
            user1_value=value1,
            user2_value=value2,
            winner=winner
        ))
    
    # Определяем общего победителя
    if user1_wins > user2_wins:
        overall_winner = 1
    elif user2_wins > user1_wins:
        overall_winner = 2
    else:
        overall_winner = 0
    
    return BattleResult(
        user1_wins=user1_wins,
        user2_wins=user2_wins,
        draws=draws,
        slot_results=slot_results,
        overall_winner=overall_winner
    )

def escape_html(text: str) -> str:
    """Экранирует HTML-символы в тексте, чтобы Telegram не пытался их парсить."""
    if not text:
        return ""
    return html_escape(text, quote=False)

def format_battle_result(result: BattleResult, user1: User, user2: User, 
                         battle_inv1: BattleInventory, battle_inv2: BattleInventory,
                         daily_verse: Optional[Verse] = None) -> str:
    """
    Отформатировать результат боя в красивое текстовое сообщение.
    """
    deck1_value = calculate_deck_value(battle_inv1)
    deck2_value = calculate_deck_value(battle_inv2)
    
    # Бонус за daily verse
    daily_name = daily_verse.name if daily_verse else None
    
    # Экранируем имена пользователей
    user1_name = escape_html(user1.name)
    user2_name = escape_html(user2.name)
    
    # Заголовок
    text = "⚔️ <b>РЕЗУЛЬТАТЫ БОЯ</b> ⚔️\n"
    text += "═══════════════════════"
    
    # Статистика игроков
    text += f"\n\n👤 <b>{user1_name}</b>\n"
    text += f"   💰 Стоимость колоды: {deck1_value} ¥\n"
    text += f"   ✨ Побед по слотам: {result.user1_wins}\n"
    
    text += "\n            🆚\n"
    
    text += f"\n👤 <b>{user2_name}</b>\n"
    text += f"   💰 Стоимость колоды: {deck2_value} ¥\n"
    text += f"   ✨ Побед по слотам: {result.user2_wins}\n"
    
    # Ничьи
    if result.draws > 0:
        text += f"\n🤝 Ничьих: {result.draws}\n"
    
    # Разделитель
    text += "\n" + "━" * 30 + "\n"
    
    # Детали по слотам
    text += "\n📋 <b>Детали по слотам:</b>\n\n"
    
    for slot_result in result.slot_results:
        slot_name = SLOT_NAMES[slot_result.slot]
        card1_name = escape_html(slot_result.user1_card.name) if slot_result.user1_card else "─ ПУСТО ─"
        card2_name = escape_html(slot_result.user2_card.name) if slot_result.user2_card else "─ ПУСТО ─"
        
        value1 = slot_result.user1_value
        value2 = slot_result.user2_value
        
        # Статус слота
        if slot_result.winner == 1:
            status = "✅"
            arrow = "→"
        elif slot_result.winner == 2:
            status = "❌"
            arrow = "←"
        else:
            status = "🤝"
            arrow = "="
        
        # Бонусы за daily verse
        bonus1 = f" (+{int(value1 * 0.2)})" if (daily_name and slot_result.user1_card and slot_result.user1_card.verse_name == daily_name) else ""
        bonus2 = f" (+{int(value2 * 0.2)})" if (daily_name and slot_result.user2_card and slot_result.user2_card.verse_name == daily_name) else ""
        
        # Форматируем строку слота
        text += f"{status} <b>{slot_name.upper()}:</b>\n"
        text += f"  ├ {card1_name} <i>({value1} ¥{bonus1})</i>\n"
        text += f"  {arrow}───────────────────\n"
        text += f"  └ {card2_name} <i>({value2} ¥{bonus2})</i>\n\n"
    
    # Итог
    text += "━" * 30 + "\n\n"
    
    # Итоговый результат
    text += "═══════════════════════\n\n"
    
    if result.overall_winner == 0:
        text += "🤝 <b>НИЧЬЯ!</b> 🤝"
    elif result.overall_winner == 1:
        text += f"🏆 <b>ПОБЕДИТЕЛЬ:</b> {user1_name} 🏆"
    else:
        text += f"🏆 <b>ПОБЕДИТЕЛЬ:</b> {user2_name} 🏆"
    
    return text

async def format_inv(battle_inv: BattleInventory, daily_verse: Verse):
    cards_list = battle_inv.cards if battle_inv.total_cards_count > 0 else []

    cards_text_parts = []
    total_value = 0

    daily_name = daily_verse.name if daily_verse else None

    for card in cards_list:
        value = await get_card_value(card, battle_inv)

        bonus = int(value * 0.2) if daily_name and card.verse_name == daily_name else 0
        total_value += value + bonus

        shiny_text = "(Shiny ✨) " if card.shiny else ""

        slot_text = ""
        for slot_attr, slot_name in SLOT_RARITY_MAP.items():
            slot_card = getattr(battle_inv, slot_name, None)
            if slot_card and slot_card.id == card.id:
                if card.rarity_name == "Лимитированный":
                    slot_text = f" [{slot_attr}]"
                break

        emoji = RARITY_EMOJIES.get(card.rarity_name, "🟡")

        cards_text_parts.append(
            f"{emoji} {card.name}{slot_text} {shiny_text}- <b>{value} ¥{f' (+{bonus})' if bonus else ''}</b>"
        )

    cards_text = "\n".join(cards_text_parts) if cards_text_parts else "Пусто..."
    cards_text += f"\n\n💰 Общая стоимость: {total_value} ¥"

    return MText.get("duels").format(cards=cards_text)