"""
Главный файл — связывает парсер и ИИ-аналитик вместе.
"""

from src.parser import fetch_articles, articles_to_text
from src.ai_analyzer import analyze
from src.config import RSS_SOURCE, MAX_ARTICLES


def main():
    print("🔍 Парсинг новостей...")
    articles = fetch_articles(RSS_SOURCE, MAX_ARTICLES)

    if not articles:
        print("❌ Не удалось загрузить статьи. Проверь RSS-ссылку или интернет.")
        return

    print(f"📥 Загружено {len(articles)} статей")

    print("🧠 Отправка в ИИ-аналитик...")
    text = articles_to_text(articles)
    result = analyze(text)

    print("\n" + "=" * 60)
    print("📊  ИТ-тренды на сегодня")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
