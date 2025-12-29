from datetime import datetime, timedelta, timezone
import json

from html import escape
from db.models import Card, Profile, User
from loguru import logger

@logger.catch
async def start_message_generator(start:bool):
    with open("app/messages.json","r") as f:
        messages = json.load(f)
    
    if start:
        return messages["first_start"]
    return  messages["start"]

@logger.catch
async def profile_tutorial():
    with open("app/messages.json","r") as f:
        messages = json.load(f)
    
    return messages["profile_tutorial"]

@logger.catch
async def profile_step2_tutorial():
    with open("app/messages.json","r") as f:
        messages = json.load(f)
    
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
    with open("app/messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)
    
    target_time = openc + timedelta(hours=3)
    
    time_left = target_time - datetime.now(timezone.utc)
    
    total_seconds = int(time_left.total_seconds())
    
    if total_seconds < 0:
        formatted_time = "00:00"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        formatted_time = f"{hours:02d}:{minutes:02d}"
    return messages["nottime"] % formatted_time

@logger.catch
async def profile_creator(profile:Profile,place_on_top:int):
    with open("app/messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)
    return messages["profile"] % (escape(profile.owner.name),profile.yens,place_on_top,
                                len(profile.owner.inventory),
                                profile.owner.joined.strftime("%d.%m.%Y"),
                                escape(profile.describe))

@logger.catch
async def not_user(name: str):
    with open("app/messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)
    return messages["not_user"] % escape(name)