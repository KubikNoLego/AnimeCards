from html import escape

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import Card, UserCards
from app.database.requests import DB
from app.utils.constants import MSK_TIMEZONE, RARITY_EMOJIES
from ..messages.MessageControl import MText


async def user_top_cards(session: AsyncSession, user_id):
        top = await session.scalars(select(Card).join(UserCards)
                                .filter_by(user_id = user_id)
                                .order_by(Card.value.desc()).limit(3))

        return "\n".join([f"{RARITY_EMOJIES.get(card.rarity.name, '🟡')} {card.name} {"(Shiny ✨) " if card.shiny else ""}- <b>{card.value} ¥</b>" for card in top])


async def user_profile(session,user_id):
        db = DB(session)
        user = await db.user.get_user(user_id)

        place_on_top = (await db.user.get_user_place_on_top(user) 
                if user.profile.visible else "?")

        text = MText.get("profile").format(
                tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
                name =  escape(user.name) + " 👑" if user.vip else escape(user.name),
                title = user.profile.title.title or "Отсутствует",
                balance = user.balance,
                pity = user.pity,
                referrals = len(user.referrals),
                top_cards = await user_top_cards(session,user_id),
                place = (place_on_top if place_on_top != "?" and 
                                place_on_top <= 99 else "99+"),
                cards = len(user.inventory),
                date = user.profile.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")

        return text