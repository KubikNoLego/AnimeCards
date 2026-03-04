from html import escape
import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import DB
from db.models import Card, UserCards
from ..func import MSK_TIMEZONE


class Messages:
    

    def __init__(self):
        self._messages = self._load_messages()

    def get(self,param:str) -> str:
        message = self._messages.get(param)
        if isinstance(message, dict):
            # Если это категория, возвращаем первый доступный ключ
            return list(message.values())[0] if message else ""
        return message

    def _load_messages(self) -> dict:
        """Загружает сообщения из всех JSON файлов в папке jsons"""
        import os
        combined_messages = {}
        
        # Получаем список всех JSON файлов в папке jsons
        jsons_dir = "app/messages/jsons"
        try:
            json_files = [f for f in os.listdir(jsons_dir) if f.endswith('.json')]
        except FileNotFoundError:
            return combined_messages
        
        # Загружаем каждый JSON файл
        for filename in json_files:
            filepath = os.path.join(jsons_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    combined_messages.update(file_data)
                    
                    # Добавляем категорию по имени файла (без расширения)
                    category_name = filename[:-5]  # Убираем .json
                    combined_messages[category_name] = file_data
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            
        return combined_messages

    def nottime(self,openc: datetime) -> str:
        """Генерировать сообщение "еще не время" с обратным отсчетом"""
        try:

            hour = 2 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 3
            target_time = openc + timedelta(hours=hour)

            time_left = target_time - datetime.now(MSK_TIMEZONE)
            total_seconds = int(time_left.total_seconds())

            if total_seconds < 0:
                formatted_time = "00:00"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                formatted_time = f"{hours:02d}:{minutes:02d}"

            return self._messages["nottime"].format(time=formatted_time)
        except Exception as e:
            # Возвращаем сообщение по умолчанию, если что-то пошло не так
            return "<i>⏳ До следующего открытия осталось немного времени</i>"

    def top_players_formatter(self,top:list,user_id:int) -> str:
        if not top:
            return "<i>🏆 Топ игроков пока пуст.</i>"

        header = "<b>🏆 Топ игроков по балансу</b>\n\n"
        players_text = []

        for i, player in enumerate(top, 1):
            place_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            highlight = "<b><i>" if player.id == user_id else ""
            end_highlight = "</i></b>" if player.id == user_id else ""

            # Создаем кликабельную ссылку на профиль пользователя
            if player.username:
                player_link = f'<a href="t.me/{player.username}">{escape(player.name)}</a>'
            else:
                player_link = escape(player.name)
            player_info = f"{place_emoji} {highlight}{player_link} — {player.balance} ¥{end_highlight}"
            players_text.append(player_info)

        return header + "\n".join(players_text)
    
    async def user_profile(self,session,user_id):
        db = DB(session)
        user = await db.get_user(user_id)

        place_on_top = await db.get_user_place_on_top(user)
        referral_rewards = sum(referral.referrer_reward for referral 
                                in user.referrals)

        text = self.get("profile").format(
            tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
            name =  escape(user.name) + " 👑" if user.vip else escape(user.name),
            balance = user.balance,
            pity = user.pity,
            referrals = len(user.referrals),
            referral_rewards = referral_rewards,
            top_cards = await self.user_top_cards(session,user_id),
            place = place_on_top,
            cards = len(user.inventory),
            date = user.profile.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")

        return text
    
    async def user_top_cards(self, session: AsyncSession, user_id):
        top = await session.scalars(select(Card).join(UserCards)
                                    .filter_by(user_id = user_id)
                                    .order_by(Card.value.desc()).limit(3))

        rarity_emojis = {
            "Обычный": "🔵",
            "Редкий": "🟢",
            "Легендарный": "🟡",
            "Мифический": "🟠",
            "Хроно": "🔴"}
        return "\n".join([f"{rarity_emojis.get(card.rarity_name, '🟡')} {card.name} {"(Shiny ✨) " if card.shiny else ""}- <b>{card.value} ¥</b>" for card in top])


MText = Messages()