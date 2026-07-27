"""
Конфигурация проекта — читает .env, при отсутствии создаёт шаблон.
"""

import os
import shutil
from dotenv import load_dotenv

# Путь к файлам .env и .env.example (относительно корня проекта)
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
_ENV_EXAMPLE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")


def _ensure_env_file() -> None:
    """
    Проверяет наличие .env при первом запуске.
    Если .env отсутствует — создаёт копию из .env.example.
    """
    if not os.path.isfile(_ENV_PATH):
        if os.path.isfile(_ENV_EXAMPLE_PATH):
            shutil.copy2(_ENV_EXAMPLE_PATH, _ENV_PATH)
            print("=" * 60)
            print("⚠️   Создан файл .env из шаблона .env.example")
            print("📝  Открой .env и заполни API-ключи перед запуском.")
            print("=" * 60)
        else:
            print("[КОНФИГ] Ошибка: не найден ни .env, ни .env.example")


# Проверяем наличие .env при импорте модуля
_ensure_env_file()
load_dotenv(_ENV_PATH)

# --- Google Gemini (по умолчанию) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- OpenAI (альтернатива Gemini) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Источник для парсинга ---
RSS_SOURCE = os.getenv("RSS_SOURCE", "https://habr.com/ru/rss/news/")
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "15"))

# --- Какой ИИ-провайдер: "gemini" (по умолчанию) или "openai" ---
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

# --- База данных ---
DB_PATH = os.getenv("DB_PATH", "data/trends.db")

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
