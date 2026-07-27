"""
Модуль для работы с SQLite — дедупликация новостей.
"""

import sqlite3
from datetime import datetime
from typing import Optional

from src.config import DB_PATH


def _get_connection() -> sqlite3.Connection:
    """Создаёт и возвращает соединение с БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # доступ к колонкам по имени
    return conn


def init_db() -> None:
    """Создаёт таблицу processed_news, если её нет."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_news (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                link        TEXT    NOT NULL UNIQUE,
                processed_at TEXT   NOT NULL
            )
        """)
        conn.commit()


def is_processed(link: str) -> bool:
    """
    Проверяет, обрабатывалась ли уже новость (по уникальной ссылке).

    Возвращает True, если новость уже есть в БД.
    """
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_news WHERE link = ?", (link,)
        ).fetchone()
        return row is not None


def is_processed_by_title(title: str) -> bool:
    """
    Проверяет, есть ли новость с таким заголовком (запасной вариант).

    Возвращает True, если заголовок уже встречался.
    """
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_news WHERE title = ? LIMIT 1",
            (title,)
        ).fetchone()
        return row is not None


def save_article(title: str, link: str) -> None:
    """
    Сохраняет обработанную новость в БД.

    Параметры:
        title — заголовок новости
        link  — прямая ссылка на новость (уникальный идентификатор)
    """
    now = datetime.now().isoformat()
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_news (title, link, processed_at) "
            "VALUES (?, ?, ?)",
            (title, link, now),
        )
        conn.commit()


def get_processed_count() -> int:
    """Возвращает общее количество обработанных новостей."""
    with _get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM processed_news").fetchone()
        return row["cnt"]
