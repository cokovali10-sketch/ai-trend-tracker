"""
Модуль работы с SQLite — дедупликация новостей и история отчётов.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from src.config import settings, path_for
from src.ai_analyzer import AnalysisResult
from src.logging_conf import get_logger

log = get_logger("db")

_DB_PATH = path_for(settings.db_path)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицы processed_news и reports, если их нет."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

    with _db() as conn:
        # WAL — параллельные чтения при фоновом анализе и просмотре дашборда
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_news (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                link         TEXT    NOT NULL UNIQUE,
                source       TEXT,
                published    TEXT,
                processed_at TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT    NOT NULL,
                news_count INTEGER,
                model      TEXT,
                overview   TEXT,
                content    TEXT,
                data       TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_processed_at ON processed_news(processed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)")
        _migrate_schema(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Добавляет недостающие колонки в старые таблицы (мягкая миграция)."""
    def columns(table: str) -> set[str]:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}

    processed_cols = columns("processed_news")
    if "source" not in processed_cols:
        conn.execute("ALTER TABLE processed_news ADD COLUMN source TEXT")
    if "published" not in processed_cols:
        conn.execute("ALTER TABLE processed_news ADD COLUMN published TEXT")


@contextmanager
def _db():
    """Контекстный менеджер: коммитит при успехе и ВСЕГДА закрывает соединение.

    Важно на Windows — иначе файл БД остаётся заблокированным.
    """
    conn = _conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- processed_news ---

def is_processed(link: str) -> bool:
    """True, если статья с такой ссылкой уже обработана."""
    with _db() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_news WHERE link = ?", (link,)
        ).fetchone()
        return row is not None


def save_article(title: str, link: str, source: str = "", published: str = "") -> None:
    """Сохраняет обработанную статью в БД (IGNORE — дубликаты пропускаются)."""
    with _db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_news (title, link, source, published, processed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, link, source, published, datetime.now().isoformat()),
        )


def get_processed_count() -> int:
    with _db() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM processed_news").fetchone()
        return row["cnt"]


# --- reports ---

def save_report(result: AnalysisResult, news_count: int) -> int:
    """Сохраняет отчёт в БД и возвращает его id."""
    content = _render_content(result)
    data = {
        "trends": [vars(t) for t in result.trends],
        "overview": result.overview,
    }
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO reports (created_at, news_count, model, overview, content, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(),
                news_count,
                result.model,
                result.overview,
                content,
                json.dumps(data, ensure_ascii=False),
            ),
        )
        return cur.lastrowid


def get_reports(limit: int = 10) -> list[sqlite3.Row]:
    """Последние отчёты (без полного content, но с data для анализа категорий)."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, created_at, news_count, model, overview, data FROM reports "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return rows


def get_report(report_id: int) -> Optional[sqlite3.Row]:
    with _db() as conn:
        return conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()


# --- статистика ---

def get_stats() -> dict:
    """Сводная статистика для CLI и дашборда."""
    with _db() as conn:
        processed = conn.execute("SELECT COUNT(*) AS c FROM processed_news").fetchone()["c"]
        reports = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]
        today = conn.execute(
            "SELECT COUNT(*) AS c FROM processed_news WHERE date(processed_at) = date('now')"
        ).fetchone()["c"]

        last7 = conn.execute(
            "SELECT date(processed_at) AS day, COUNT(*) AS cnt "
            "FROM processed_news GROUP BY day ORDER BY day DESC LIMIT 7"
        ).fetchall()

        models = conn.execute(
            "SELECT model, COUNT(*) AS cnt FROM reports WHERE model != '' GROUP BY model"
        ).fetchall()

        last_report = conn.execute(
            "SELECT created_at FROM reports ORDER BY id DESC LIMIT 1"
        ).fetchone()

    return {
        "processed": processed,
        "reports": reports,
        "today": today,
        "last7": [{"day": r["day"], "count": r["cnt"]} for r in reversed(list(last7))],
        "models": [{"model": r["model"], "count": r["cnt"]} for r in models],
        "last_report_at": last_report["created_at"] if last_report else None,
    }


def _render_content(result: AnalysisResult) -> str:
    """Текст отчёта для хранения (markdown-подобный)."""
    lines = [f"# ИТ-тренды ({result.model or 'AI'})", ""]
    for i, t in enumerate(result.trends, 1):
        lines.append(f"## {i}. {t.title}")
        lines.append(f"- Категория: {t.category} | Эмоция: {t.sentiment}")
        lines.append(t.summary)
        if t.importance:
            lines.append(f"Почему важно: {t.importance}")
        if t.link:
            lines.append(f"Источник: {t.link}")
        lines.append("")
    if result.overview:
        lines.append(f"**Вывод:** {result.overview}")
    return "\n".join(lines)
