# Стандартные библиотеки
from pathlib import Path
from os.path import join, dirname

# Сторонние библиотеки
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Путь к корню проекта (на два уровня выше этого файла)
PROJECT_ROOT = Path(__file__).parent.parent

class Config(BaseSettings):
    BOT_TOKEN: SecretStr
    DB_URL: SecretStr
    REDIS_URL: SecretStr
    MESSAGE_ID: int
    CHAT_ID: str

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8"
    )

config = Config()
