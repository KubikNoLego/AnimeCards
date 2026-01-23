# Стандартные библиотеки
import json
import math
import os
import random
import tempfile
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Optional

# Сторонние библиотеки
import qrcode
from aiogram.types import FSInputFile, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Локальные импорты
from db import Card, Clan, Profile, User, Verse,RedisRequests,DB

# Константы для генерации случайных карт
RARITIES = [1, 2, 3, 4, 5]
CHANCES = [55, 27, 12, 4.5, 1]
SHINY_CHANCE = 0.05


class Text:

    def _load_messages(self) -> dict:
        """Загружает сообщения из JSON"""
        with open("app/messages.json", "r", encoding="utf-8") as f:
            messages_data = json.load(f)

        # Объединяем сообщения из категорий для обратной совместимости
        combined_messages = {}
        combined_messages.update(messages_data.get("success_messages", {}))
        combined_messages.update(messages_data.get("error_messages", {}))

        # Добавляем категории для прямого доступа
        combined_messages["success_messages"] = messages_data.get("success_messages", {})
        combined_messages["error_messages"] = messages_data.get("error_messages", {})
        return combined_messages

    @logger.catch
    async def start_message_generator(self,start: bool) -> str:
        """Генерировать стартовое сообщение на основе статуса пользователя"""
        messages = self._load_messages()
        key = "first_start" if start else "start"
        return messages[key]

    @logger.catch
    async def profile_tutorial(self) -> str:
        """Получить сообщение-руководство для профиля (шаг 1)."""
        messages = self._load_messages()
        return messages["profile_tutorial"]

    @logger.catch
    async def nottime(self,openc: datetime) -> str:
        """Генерировать сообщение "еще не время" с обратным отсчетом"""
        try:
            messages = self._load_messages()

            # Используем ту же логику, что и в messages.py: 2 часа в будни, 3 часа в выходные
            hour = 2 if datetime.now(timezone.utc).weekday() >= 5 else 3
            # Целевое время — открытие + hour часов (локальная корректировка)
            target_time = openc + timedelta(hours=hour)

            time_left = target_time - datetime.now(timezone.utc)
            total_seconds = int(time_left.total_seconds())

            if total_seconds < 0:
                formatted_time = "00:00"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                formatted_time = f"{hours:02d}:{minutes:02d}"

            return messages["nottime"] % formatted_time
        except Exception as e:
            # Возвращаем сообщение по умолчанию, если что-то пошло не так
            return "<i>⏳ До следующего открытия осталось немного времени</i>"

    @logger.catch
    async def profile_creator(self,clan: Clan,profile: Profile,
                            place_on_top: int, session: AsyncSession) -> str:
        """Создать отображение профиля пользователя"""
        messages = self._load_messages()

        owner = profile.owner

        collections_count = await DB(session).get_user_collections_count(owner)

        return messages["profile"] % (
            ((f"<b>[{clan.tag}]</b> ") if clan else "") + escape(owner.name) + (" 👑" if owner.vip else ""),
            profile.yens,
            place_on_top,
            len(owner.inventory),
            collections_count,
            owner.joined.strftime("%d.%m.%Y"),
            f"«{escape(profile.describe)}»" if profile.describe != "" else "",
        )

    @logger.catch
    async def not_user(self,name: str) -> str:
        """Генерировать сообщение "пользователь не найден"""
        messages = self._load_messages()
        return messages["not_user"] % escape(name)

    @logger.catch
    async def top_players_formatter(self,top_players: list,
                                    current_user_id: int) -> str:
        """Форматировать список топ игроков по балансу"""
        messages = self._load_messages()

        if not top_players:
            return "<i>🏆 Топ игроков пока пуст.</i>"

        header = "<b>🏆 Топ игроков по балансу</b>\n\n"
        players_text = []

        for i, player in enumerate(top_players, 1):
            place_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            highlight = "<b><i>" if player.id == current_user_id else ""
            end_highlight = "</i></b>" if player.id == current_user_id else ""

            # Создаем кликабельную ссылку на профиль пользователя
            player_link = f'<a href="tg://user?id={player.id}">{escape(player.name)}</a>'
            player_info = f"{place_emoji} {highlight}{player_link} — {player.yens} ¥{end_highlight}"
            players_text.append(player_info)

        return header + "\n".join(players_text)

    @logger.catch
    async def profile_step2_tutorial(self) -> str:
        """Получить сообщение-руководство для профиля (шаг 2)."""
        messages = self._load_messages()
        return messages["profile_tutorial2"]

    @logger.catch
    async def card_formatter(self,card: Card, user: User = None) -> str:
        """Форматировать информацию о карте для отображения"""
        vip_bonus = ""
        if user and user.vip:
            bonus_amount = math.ceil(card.value * 0.1)
            vip_bonus = f" (+{bonus_amount} ¥)"

        return f"""
    📄 <b>{card.name}</b>
    📚 Вселенная: {card.verse.name}
    🎨 Редкость: {card.rarity.name}
    💰 Ценность: {card.value} ¥{vip_bonus}
    {"✨ Shiny" if card.shiny else ""}
    """

async def create_qr(link:str) -> FSInputFile:
    """Создаёт QR для реферальной ссылки"""
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(link)

    # Создаем временный файл
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    try:
        # Генерируем изображение и сохраняем во временный файл
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(temp_file.name)
        return FSInputFile(temp_file.name)
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise
async def random_card(session: AsyncSession, pity: int) -> Card:
    """Выбрать случайную карту"""
    # Выбор редкости: если есть `pity` — используем веса, иначе выдаём самую дорогую редкость (5)
    random_rarity = random.choices(RARITIES, CHANCES, k=1)[0] if pity > 0 else 5
    # Определяем, выпала ли shiny-версия
    is_shiny = random.random() < SHINY_CHANCE

    # Оптимизация: получаем daily_verse параллельно с запросом к базе данных
    daily_verse_task = RedisRequests.daily_verse()

    cards_result = await session.scalars(
        select(Card).where(
            Card.shiny == is_shiny,
            Card.can_drop == True,
            Card.rarity.has(id=random_rarity),
        )
    )
    cards = cards_result.all()

    if not cards:
        raise ValueError(f"Нет доступных карт с редкостью {random_rarity} и shiny={is_shiny}")

    daily_verse = await daily_verse_task

    # Оптимизация: используем list comprehension вместо циклов для разделения карт
    if daily_verse:
        boosted_cards = [card for card in cards if card.verse.id == daily_verse]
        normal_cards = [card for card in cards if card.verse.id != daily_verse]

        # Увеличиваем шанс на 25% для карт из ежедневной вселенной
        if boosted_cards:
            cards = random.choices(
                population=boosted_cards + normal_cards,
                weights=[1.25] * len(boosted_cards) + [1.0] * len(normal_cards),
                k=1
            )
            return cards[0]

    return random.choice(cards) if cards else None

async def user_photo_link(message: Message) -> Optional[str]:
    """Получить file_id фото профиля пользователя"""
    try:
        # Определяем чей профиль запрашивать: reply target имеет приоритет
        target_id = message.reply_to_message.from_user.id if message.reply_to_message and message.reply_to_message.from_user else message.from_user.id

        profile_photos = await message.bot.get_user_profile_photos(target_id, limit=1)

        # Проверяем, есть ли хоть одна фотография
        if profile_photos and len(profile_photos.photos) > 0:
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id
            return file_id
    except Exception as exc:
        # Логируем исключение с трассировкой для удобства отладки
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

    return None



