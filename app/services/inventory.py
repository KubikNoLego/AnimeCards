from app.database.models import Card, UserCards
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_

async def sort_inventory(user_id: int,
                        selected_rarity_name: str,
                        selected_verse_name: str, index: int,
                        session: AsyncSession) -> Card:
    conditions = [UserCards.user_id == user_id]
    if selected_rarity_name:
        conditions.append(card.rarity.name == selected_rarity_name)
    if selected_verse_name:
        conditions.append(card.verse.name == selected_verse_name)
    
    stmt = (
    select(Card)
    .join(UserCards)
    .where(and_(*conditions))
    .order_by(UserCards.id)
    .limit(1)
    .offset(index))

    card = await session.scalar(stmt)

    count_stmt = (
    select(func.count())
    .select_from(UserCards)
    .join(Card)
    .where(and_(*conditions))
    )

    total_cards = await session.scalar(count_stmt)

    return card, total_cards
