"""
Главный файл — связывает парсер, БД, ИИ-аналитик и Telegram-уведомления.

Логика работы:
  1. Парсим RSS → получаем список статей.
  2. Инициализируем БД.
  3. Фильтруем: оставляем ТОЛЬКО те статьи, которых ещё нет в БД.
  4. Если новых нет → завершаемся.
  5. Отправляем новые статьи в ИИ → получаем краткую сводку.
  6. Сохраняем обработанные статьи в БД (чтобы повторно не слать).
  7. Отправляем сводку в Telegram и выводим в консоль.
"""

from src.parser import fetch_articles, articles_to_text
from src.ai_analyzer import analyze
from src.config import RSS_SOURCE, MAX_ARTICLES
from src.database import init_db, is_processed, save_article, get_processed_count
from src.notifier import send_telegram


def main() -> None:
    print("🔍 Парсинг новостей...")
    articles = fetch_articles(RSS_SOURCE, MAX_ARTICLES)

    if not articles:
        print("❌ Не удалось загрузить статьи. Проверь RSS-ссылку или интернет.")
        return

    print(f"📥 Загружено {len(articles)} статей")

    # Инициализация БД
    init_db()
    print(f"🗄️  Всего обработано ранее: {get_processed_count()}")

    # Фильтрация дубликатов
    new_articles = [
        art for art in articles if not is_processed(art.link)
    ]

    if not new_articles:
        print("✅ Новых статей нет. Выход.")
        return

    print(f"🆕 Новых статей: {len(new_articles)}")

    # Отправка в ИИ
    print("🧠 Отправка в ИИ-аналитик...")
    text = articles_to_text(new_articles)
    result = analyze(text)

    # Сохранение обработанных статей в БД
    for art in new_articles:
        save_article(art.title, art.link)
    print(f"💾 Сохранено {len(new_articles)} статей в БД")

    # Отправка в Telegram
    send_telegram(result)

    # Вывод в консоль
    print("\n" + "=" * 60)
    print("📊  ИТ-тренды на сегодня")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
