from datetime import datetime, timedelta, timezone
import json

from html import escape
from db.models import Card, Profile, User
from loguru import logger

@logger.catch
async def start_message_generator(start:bool):
    # Возвращает стартовое сообщение в зависимости от флага
    messages = _load_messages()
    key = "first_start" if start else "start"
    logger.info(f"Возвращаю стартовое сообщение: {key}")
    return messages[key]

@logger.catch
async def profile_tutorial():
    messages = _load_messages()
    logger.info("Возвращаю сообщение-руководство для профиля (шаг 1)")
    return messages["profile_tutorial"]

@logger.catch
async def profile_step2_tutorial():
    messages = _load_messages()
    logger.info("Возвращаю сообщение-руководство для профиля (шаг 2)")
    return messages["profile_tutorial2"]

@logger.catch
async def card_formatter(card:Card):
    return f"""
📄 <b>{card.name}</b>
📚 Вселенная: {card.verse.name}
🎨 Редкость: {card.rarity.name}
💰 Ценность: {card.value} ¥
{"✨ Shiny" if card.shiny else ""}
"""

@logger.catch
async def nottime(openc:datetime):
    messages = _load_messages()

    # Целевое время — открытие + 3 часа (локальная корректировка)
    target_time = openc + timedelta(hours=3)

    time_left = target_time - datetime.now(timezone.utc)
    total_seconds = int(time_left.total_seconds())

    if total_seconds < 0:
        formatted_time = "00:00"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        formatted_time = f"{hours:02d}:{minutes:02d}"

    logger.info(f"Осталось до следующего открытия: {formatted_time}")
    return messages["nottime"] % formatted_time

@logger.catch
async def profile_creator(profile:Profile,place_on_top:int):
    messages = _load_messages()

    owner = profile.owner
    logger.info(f"Генерирую профиль для пользователя id={getattr(owner, 'id', None)}")
    return messages["profile"] % (
        escape(owner.name),
        profile.yens,
        place_on_top,
        len(owner.inventory),
        owner.joined.strftime("%d.%m.%Y"),
        escape(profile.describe),
    )

@logger.catch
async def not_user(name: str):
    messages = _load_messages()
    logger.warning(f"Запрос для несуществующего пользователя: {name}")
    return messages["not_user"] % escape(name)


def _load_messages() -> dict:
    """Helper: загружает JSON с сообщениями (кодировка utf-8)."""
    with open("app/messages.json", "r", encoding="utf-8") as f:
        return json.load(f)