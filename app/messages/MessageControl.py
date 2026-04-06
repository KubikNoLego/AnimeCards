from html import escape
import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DB
from app.database.models import Card, UserCards
from ..utils.consts import MSK_TIMEZONE, RARITY_EMOJIES


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

MText = Messages()