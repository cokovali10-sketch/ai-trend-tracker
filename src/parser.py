"""
Модуль парсинга — собирает статьи из одного или нескольких RSS-источников.
"""

import html as html_mod
import re
from dataclasses import dataclass

import feedparser
import requests

from src.logging_conf import get_logger
# --- константы вынесены FORGE refactor ---
CONST_15 = 15


log = get_logger("parser")

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_HTTP_TIMEOUT = CONST_15  # секунд
_USER_AGENT = "Mozilla/5.0 (AI-Trend-Tracker/2.0; +https://github.com)"


@dataclass
class Article:
    """Структура одной статьи."""
    title: str
    link: str
    summary: str
    published: str
    source: str = ""


def clean_html(raw: str) -> str:
    """Убирает HTML-теги и лишние пробелы, разворачивает сущности."""
    text = _TAG_RE.sub(" ", raw or "")
    text = html_mod.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _fetch_feed_bytes(rss_url: str) -> bytes:
    """Скачивает RSS-ленту с таймаутом. Бросает requests.RequestException."""
    resp = requests.get(
        rss_url,
        timeout=_HTTP_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    )
    resp.raise_for_status()
    return resp.content


def fetch_articles(rss_url: str, max_count: int = CONST_15) -> list[Article]:
    """Парсит одну RSS-ленту и возвращает до max_count статей."""
    log.info("Парсим источник: %s", rss_url)
    try:
        content = _fetch_feed_bytes(rss_url)
        feed = feedparser.parse(content)
    except requests.RequestException as e:
        log.error("Ошибка загрузки %s: %s", rss_url, e)
        return []
    except Exception as e:  # noqa: BLE001
        log.error("Непредвиденная ошибка при загрузке %s: %s", rss_url, e)
        return []

    if feed.bozo and not feed.entries:
        log.error("Не удалось распарсить %s: %s", rss_url, feed.bozo_exception)
        return []

    articles = []
    for entry in feed.entries[:max_count]:
        articles.append(Article(
            title=clean_html(entry.get("title", "Без заголовка")),
            link=entry.get("link", "").strip(),
            summary=clean_html(entry.get("summary") or entry.get("description") or ""),
            published=entry.get("published") or entry.get("updated") or "Дата неизвестна",
            source=rss_url,
        ))
    log.info("Получено статей: %d", len(articles))
    return articles


def fetch_all_sources(urls: list[str], max_count_per_source: int = CONST_15) -> list[Article]:
    """Собирает статьи из всех источников, убирая дубликаты по ссылке."""
    seen: set[str] = set()
    result: list[Article] = []
    for url in urls:
        for art in fetch_articles(url, max_count_per_source):
            key = art.link or art.title
            if key in seen:
                continue
            seen.add(key)
            result.append(art)
    return result


def articles_to_text(articles: list[Article], max_chars: int = 800) -> str:
    """Преобразует список статей в текст для отправки в ИИ."""
    lines = []
    for i, art in enumerate(articles, 1):
        lines.append(f"--- Статья {i} ---")
        lines.append(f"Заголовок: {art.title}")
        lines.append(f"Ссылка: {art.link}")
        lines.append(f"Дата: {art.published}")
        lines.append(f"Кратко: {art.summary[:max_chars]}")
        lines.append("")
    return "\n".join(lines)
