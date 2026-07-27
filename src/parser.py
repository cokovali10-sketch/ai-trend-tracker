"""
Модуль парсинга — собирает свежие статьи из RSS-ленты.
"""

import feedparser
from dataclasses import dataclass


@dataclass
class Article:
    """Структура одной статьи."""
    title: str
    link: str
    summary: str
    published: str


def fetch_articles(rss_url: str, max_count: int = 15) -> list[Article]:
    """
    Парсит RSS-ленту и возвращает список статей.

    Параметры:
        rss_url: адрес RSS-ленты (например, https://habr.com/ru/rss/news/)
        max_count: максимальное количество статей для загрузки

    Возвращает:
        список объектов Article
    """
    feed = feedparser.parse(rss_url)

    if feed.bozo and not feed.entries:
        print(f"[ОШИБКА] Не удалось распарсить RSS: {feed.bozo_exception}")
        return []

    articles = []
    for entry in feed.entries[:max_count]:
        title = entry.get("title", "Без заголовка")
        link = entry.get("link", "")
        # summary может быть в разных полях в зависимости от ленты
        summary = entry.get("summary") or entry.get("description") or ""
        published = entry.get("published", "Дата неизвестна")

        articles.append(Article(
            title=title,
            link=link,
            summary=summary,
            published=published,
        ))

    return articles


def articles_to_text(articles: list[Article]) -> str:
    """
    Преобразует список статей в единый текст для отправки в ИИ.
    """
    lines = []
    for i, art in enumerate(articles, 1):
        lines.append(f"--- Статья {i} ---")
        lines.append(f"Заголовок: {art.title}")
        lines.append(f"Ссылка: {art.link}")
        lines.append(f"Дата: {art.published}")
        # Обрезаем summary до 800 символов, чтобы не превышать лимит токенов
        summary_clean = art.summary[:800]
        lines.append(f"Кратко: {summary_clean}")
        lines.append("")

    return "\n".join(lines)
