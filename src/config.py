"""
Конфигурация проекта — читает .env, при отсутствии создаёт шаблон.
Все настройки доступны через синглтон `settings`.
"""

import os
import shutil
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv
# --- константы вынесены FORGE refactor ---
CONST_4 = 4
CONST_15 = 15
CONST_60 = 60


# Принудительный UTF-8 вывод — без этого эмодзи в консоли Windows (cp1251) роняют скрипт
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")
_ENV_EXAMPLE_PATH = os.path.join(_BASE_DIR, ".env.example")


def path_for(rel: str) -> str:
    """Превращает относительный путь в абсолютный (от корня проекта)."""
    if os.path.isabs(rel):
        return rel
    return os.path.join(_BASE_DIR, rel)


def _ensure_env_file() -> None:
    """Если .env нет — создаёт копию из .env.example."""
    if not os.path.isfile(_ENV_PATH):
        if os.path.isfile(_ENV_EXAMPLE_PATH):
            shutil.copy2(_ENV_EXAMPLE_PATH, _ENV_PATH)
            print("=" * CONST_60)
            print("⚠️   Создан файл .env из шаблона .env.example")
            print("📝  Открой .env и заполни API-ключи перед запуском.")
            print("=" * CONST_60)
        else:
            print("[КОНФИГ] Ошибка: не найден ни .env, ни .env.example")


def _csv_list(value: str) -> list[str]:
    """Разбирает строку вида 'a, b, c' в список."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_int(name: str, default: int) -> int:
    """Безопасное чтение целого из env — при мусоре возвращает default."""
    try:
        return int(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """Безопасное чтение числа с плавающей точкой из env."""
    try:
        return float(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default


def _mask_secret(value: str) -> str:
    """Маскирует секрет для показа: первые 4 и последние 4 символа."""
    value = value or ""
    if len(value) <= 8:
        return "***"
    return f"{value[:CONST_4]}…{value[-CONST_4:]}"


def _safe_bool(value: str) -> bool:
    """Читает булево значение '1/true/yes/on' → True."""
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Все настройки приложения."""

    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    rss_sources: list[str] = field(default_factory=lambda: ["https://habr.com/ru/rss/news/"])
    max_articles: int = CONST_15
    db_path: str = "data/trends.db"
    reports_dir: str = "data/reports"
    log_level: str = "INFO"
    log_file: str = "logs/trends.log"
    telegram_bot_token: str = ""
    telegram_chat_ids: list[str] = field(default_factory=list)
    run_interval_min: int = CONST_60
    bot_poll_interval: float = 2.0
    export_format: str = "md"
    notify_enabled: bool = True

    # --- Свойства ---
    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_ids)

    @property
    def provider_name(self) -> str:
        return "Gemini" if self.ai_provider == "gemini" else "OpenAI"

    @property
    def model_name(self) -> str:
        return self.gemini_model if self.ai_provider == "gemini" else self.openai_model

    @property
    def telegram_token_masked(self) -> str:
        return _mask_secret(self.telegram_bot_token)

    @property
    def gemini_key_masked(self) -> str:
        return _mask_secret(self.gemini_api_key)

    @property
    def openai_key_masked(self) -> str:
        return _mask_secret(self.openai_api_key)

    def secrets_masked(self) -> dict:
        """Все секреты в замаскированном виде (для команды `config`)."""
        return {
            "GEMINI_API_KEY": self.gemini_key_masked,
            "OPENAI_API_KEY": self.openai_key_masked,
            "TELEGRAM_BOT_TOKEN": self.telegram_token_masked,
        }

    def as_table(self) -> dict:
        """Все настройки в виде словаря (для команды `config`)."""
        return {
            "AI_PROVIDER": self.provider_name,
            "MODEL": self.model_name,
            "RSS_SOURCES": "; ".join(self.rss_sources),
            "MAX_ARTICLES": str(self.max_articles),
            "DB_PATH": self.db_path,
            "REPORTS_DIR": self.reports_dir,
            "LOG_LEVEL": self.log_level,
            "LOG_FILE": self.log_file,
            "TELEGRAM": "вкл" if self.telegram_enabled else "выкл",
            "TELEGRAM_CHATS": ", ".join(self.telegram_chat_ids) or "—",
            "RUN_INTERVAL_MIN": str(self.run_interval_min),
            "EXPORT_FORMAT": self.export_format,
        }

    def warnings(self) -> list[str]:
        """Возвращает список проблем конфигурации (для показа при запуске)."""
        warns = []
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            warns.append("GEMINI_API_KEY не задан в .env")
        if self.ai_provider == "openai" and not self.openai_api_key:
            warns.append("OPENAI_API_KEY не задан в .env")
        if not self.telegram_enabled:
            warns.append("Telegram не настроен (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        if not self.rss_sources:
            warns.append("RSS_SOURCES пуст — используется Habr по умолчанию")
        return warns

    @classmethod
    def from_env(cls) -> "Settings":
        _ensure_env_file()
        load_dotenv(_ENV_PATH, override=False)

        sources = _csv_list(os.getenv("RSS_SOURCES", ""))
        if not sources:
            sources = ["https://habr.com/ru/rss/news/"]
        # Поддержка старого имени переменной + множественных чатов
        chat_ids = _csv_list(os.getenv("TELEGRAM_CHAT_IDS", "") or os.getenv("TELEGRAM_CHAT_ID", ""))

        return cls(
            ai_provider=os.getenv("AI_PROVIDER", "gemini").lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            rss_sources=sources,
            max_articles=_env_int("MAX_ARTICLES", CONST_15),
            db_path=os.getenv("DB_PATH", "data/trends.db").strip(),
            reports_dir=os.getenv("REPORTS_DIR", "data/reports").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("LOG_FILE", "logs/trends.log").strip(),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_ids=chat_ids,
            run_interval_min=_env_int("RUN_INTERVAL_MIN", CONST_60),
            bot_poll_interval=_env_float("BOT_POLL_INTERVAL", 2.0),
            export_format=(os.getenv("EXPORT_FORMAT", "md").lower() or "md"),
            notify_enabled=not _safe_bool(os.getenv("NOTIFY_DISABLED", "")),
        )


settings = Settings.from_env()
