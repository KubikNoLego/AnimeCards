import json
from kubiks import load


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
        """Загружает сообщения из всех JSON и KBK файлов в папке jsons"""
        import os
        combined_messages = {}

        # Получаем список всех JSON и KBK файлов в папке jsons
        jsons_dir = "app/messages/jsons"
        try:
            json_files = [f for f in os.listdir(jsons_dir) if f.endswith('.json')]
            kbk_files = [f for f in os.listdir(jsons_dir) if f.endswith('.kbk')]
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

        # Загружаем каждый KBK файл с помощью kubiks.load
        for filename in kbk_files:
            filepath = os.path.join(jsons_dir, filename)
            try:
                kbk_data = load(filepath)
                combined_messages.update(kbk_data)

                # Добавляем категорию по имени файла (без расширения)
                category_name = filename[:-4]  # Убираем .kbk
                combined_messages[category_name] = kbk_data
            except (FileNotFoundError, Exception):
                continue

        return combined_messages

MText = Messages()