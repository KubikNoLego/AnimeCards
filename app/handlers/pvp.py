from aiogram import Router,F
from aiogram.types import Message,FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.messages import MText
from db import DB, Verse, RedisRequests

router = Router()

@router.message(F.text == "⚔️ Дуэли", Private())
async def _(message:Message,session:AsyncSession):
    db = DB(session)
    daily_verse = await session.scalar(select(Verse).filter_by(
        id= await RedisRequests.daily_verse()))
    user = await db.get_user(message.from_user.id)

    if not user.clan_member:
        await message.answer("user_not_in_clan_pvp")
        return
    
    if not user.battle_inventory:
        inventory = await db.create_battle_inventory(user)
    
    rarity_emojis = {
            "Обычный": "🔵",
            "Редкий": "🟢",
            "Легендарный": "🟡",
            "Мифический": "🟠",
            "Хроно": "🔴"}

    cards_text = ("\n".join([f"{rarity_emojis.get(card.rarity_name, '🟡')} {card.name} {"(Shiny ✨) " if card.shiny else ""}- <b>{card.value} ¥{f" (+{int(card.value*0.2)}) ¥" if card.verse_name == daily_verse.name else ""}</b>" for card in user.battle_inventory.cards])) if user.battle_inventory.total_cards_count > 0 else "Пусто..."

    cards_text += f"\n\n💰 Общая стоимость: {sum([card.value if card.verse_name != daily_verse.name else int(card.value*1.2) for card in user.battle_inventory.cards])} ¥"

    await message.answer(MText.get("duels").format(cards=cards_text))