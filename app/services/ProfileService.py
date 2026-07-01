from datetime import datetime, timedelta
import os
import random
import tempfile

from aiogram import Bot
from aiogram.types import FSInputFile
from loguru import logger
import qrcode
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, UserCards, Profile, Card
from app.database.requests import DB
from app.messages.MessageControl import MText
from app.utils.constants import MSK_TIMEZONE, RARITY_EMOJIES
from app.utils.plural import plural

class ProfileService:

    @classmethod
    async def user_photo_link(cls, bot: Bot, user_id: int) -> str | None:
        """Получить file_id фото профиля пользователя"""
        try:

            profile_photos = await bot.get_user_profile_photos(
                                                            user_id,
                                                            limit=1
                                                            )

            if profile_photos and len(profile_photos.photos) > 0:
                photo = profile_photos.photos[0][-1]
                file_id = photo.file_id
                return file_id
            else:
                return None
        except Exception as exc:
            logger.exception(f"Ошибка при получении фото пользователя: {exc}")

            return None
        
    @classmethod
    async def best_cards(cls, user: User, session: AsyncSession) -> str:

        cards = (await session.scalars(select(UserCards)
                                    .join(Card)
                                    .where(UserCards.user_id == user.id)
                                    .order_by(Card.value.desc())
                                    .limit(3))).all()
        

        format_cards = "\n".join(
            [f"{RARITY_EMOJIES.get(usercard.card.rarity.name, '🟡')} {usercard.card.name} {"(Shiny ✨) " if usercard.shiny else ""}- <b>{usercard.card.price(usercard.shiny)} ¥</b>" for usercard in cards])


        return format_cards
    
    @classmethod
    async def generate_profile(cls, session: AsyncSession, user_id: int):

        db = DB(session)
        user = await db.user.get_user(user_id)

        have_clan = user.clan_member
        all_cards_count = await cls.all_cards(session)
        shiny_count = sum(usercard.shiny for usercard in user.inventory)
        collection_sum = sum(usercard.card.price(usercard.shiny) for usercard in user.inventory)
        days = (datetime.now(MSK_TIMEZONE) - user.profile.joined).days

        profile_text = """👤 {name}
🆔 <code>{user_id}</code>
🏷 <b>{title}</b>
🏰 <b>{clan_tag}</b><i>{clan_name}</i>

💰 <b>{balance}</b> ¥
🏆 #<b>{top_place}</b> сезона

📚 <b>{cards}/{all_cards}</b> <i>({percent}%)</i>
✨ Shiny: <b>{shiny}</b>
💎 Коллекция: <b>{collection_sum} ¥</b>

⭐️ Лучшие карты
<blockquote>{best_cards}</blockquote>

🕒 В игре: {days} {word}"""

        return profile_text.format(
            name = user.name + (" ⟦ 👑 ⟧" if user.vip else ''),
            user_id = user.id,
            title = user.profile.title.name,
            clan_tag = f"[{have_clan.clan.tag}] " if have_clan else "",
            clan_name = have_clan.clan.name if have_clan else "-",
            balance = f"{user.balance:,}",
            top_place = await db.user.get_user_place_on_top(user),
            cards = len(user.inventory),
            all_cards = all_cards_count,
            percent = int((len(user.inventory)/all_cards_count)*100),
            shiny = shiny_count,
            collection_sum = f"{collection_sum:,}",
            best_cards = await cls.best_cards(user, session),
            days = days,
            word = plural(days, "день", "дня", "дней")
        )
    
    @classmethod
    async def all_cards(cls, session: AsyncSession):
    
        return int(await session.scalar(select(func.count(Card.id))
                                    .where(Card.droppable == True)))
    
    @classmethod
    def create_qr(link:str) -> FSInputFile:
        """Создаёт QR для реферальной ссылки"""
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4
        )
        qr.add_data(link)
    
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        try:
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(temp_file.name)
            return FSInputFile(temp_file.name)
        except Exception as e:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            logger.exception("Ошибкв при создании QR")
            return

