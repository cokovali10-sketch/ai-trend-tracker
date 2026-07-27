import os
from dotenv import load_dotenv

load_dotenv()

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Google Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Источник для парсинга ---
# RSS-лента Habr News (можно заменить на любой другой RSS)
RSS_SOURCE = os.getenv("RSS_SOURCE", "https://habr.com/ru/rss/news/")

# Сколько статей загружать за раз
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "15"))

# Какой ИИ-провайдер используется: "openai" или "gemini"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
