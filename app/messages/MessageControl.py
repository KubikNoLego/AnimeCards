from html import escape
import yaml
from datetime import datetime,timezone,timedelta

MSK_TIMEZONE = timezone(timedelta(hours=3))


class Messages:
    

    def __init__(self):
        self._messages = self._load_messages()

    def get(self,param:str) -> str:
        return self._messages[param]

    def reload(self) -> None:
        self._messages = self._load_messages()
        return
    def _load_messages(self) -> dict:
        """Загружает сообщения из JSON"""
        with open("app/messages/messages.yaml", "r", encoding="utf-8") as f:
            messages_data = yaml.safe_load(f)

        # Объединяем сообщения из категорий для обратной совместимости
        combined_messages = {}
        combined_messages.update(messages_data.get("success_messages", {}))
        combined_messages.update(messages_data.get("error_messages", {}))

        # Добавляем категории для прямого доступа
        combined_messages["success_messages"] = messages_data.get("success_messages", {})
        combined_messages["error_messages"] = messages_data.get("error_messages", {})
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
            player_link = f'<a href="tg://openmessage?user_id={player.id}">{escape(player.name)}</a>'
            player_info = f"{place_emoji} {highlight}{player_link} — {player.balance} ¥{end_highlight}"
            players_text.append(player_info)

        return header + "\n".join(players_text)

MText = Messages()