# AI Trend Tracker

Умный парсер + ИИ-аналитик ИТ-трендов: собирает свежие посты из RSS, отправляет в LLM (Gemini/OpenAI), выделяет ТОП-3 трендов и отправляет отчёт в Telegram. Имеет веб-дашборд и красивый CLI.

## Возможности

- 📡 Парсинг одного или нескольких RSS-источников (по умолчанию Habr News), с таймаутами загрузки
- 🧠 Структурированный ИИ-анализ: категории, сентимент, важность, ссылки на источники (JSON-схема ответа)
- 🔁 Автодедупликация новостей через SQLite (WAL — параллельный доступ CLI и дашборда)
- 🔄 Ротация моделей Gemini при исчерпании квоты + повтор при 429
- 📜 История отчётов в БД + экспорт в Markdown / HTML / JSON
- ✈️ Отправка отчётов в Telegram (HTML-разметка, несколько чатов, разбивка длинных сообщений)
- 🖥️ Веб-дашборд: статистика, график активности, категории трендов, просмотр отчётов, запуск анализа
- 🤖 Интерактивный Telegram-бот: /today, /stats, /recent, /model, /help
- 🎨 Красивый CLI на `rich` с подкомандами (включая `config`)
- 📝 Логирование в консоль и файл (с ротацией)

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env          # Windows
# заполни GEMINI_API_KEY (или OPENAI_API_KEY) и Telegram-ключи
```

Файл `.env` создаётся автоматически из `.env.example` при первом запуске, если его нет.

## Запуск

```bash
python main.py run          # полный цикл: парсинг → ИИ → БД → Telegram → экспорт
python main.py run --no-telegram --no-export
python main.py run --export-format html   # отчёт в HTML вместо Markdown
python main.py run --loop --every 60     # по расписанию каждые 60 минут
python main.py bot          # интерактивный Telegram-бот (/today, /stats, /recent, /help)
python main.py reports      # список последних отчётов
python main.py show 3       # показать отчёт #3
python main.py stats        # статистика по БД
python main.py config       # текущая конфигурация (секреты скрыты)
python main.py dashboard    # запустить веб-дашборд (http://127.0.0.1:5000)
python webapp.py            # то же самое, напрямую
```

### Docker

```bash
docker build -t ai-trend-tracker .
docker run -p 5000:5000 -v "$(pwd)/data:/app/data" -v "$(pwd)/logs:/app/logs" ai-trend-tracker
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `GEMINI_API_KEY` | Ключ Gemini | — |
| `GEMINI_MODEL` | Модель Gemini | `gemini-3.5-flash-lite` |
| `OPENAI_API_KEY` | Ключ OpenAI (альтернатива) | — |
| `OPENAI_MODEL` | Модель OpenAI | `gpt-4o-mini` |
| `AI_PROVIDER` | `gemini` или `openai` | `gemini` |
| `RSS_SOURCES` | Источники через запятую | Habr News |
| `MAX_ARTICLES` | Макс. статей на источник | `15` |
| `DB_PATH` | Файл SQLite | `data/trends.db` |
| `REPORTS_DIR` | Папка экспорта отчётов | `data/reports` |
| `LOG_LEVEL` | Уровень логов | `INFO` |
| `LOG_FILE` | Файл логов | `logs/trends.log` |
| `TELEGRAM_BOT_TOKEN` | Токен бота (@BotFather) | — |
| `TELEGRAM_CHAT_ID` | ID чата(ов), через запятую | — |
| `NOTIFY_DISABLED` | `1` — отключить отправку отчётов | — |
| `RUN_INTERVAL_MIN` | Интервал по умолчанию для `run --loop` | `60` |
| `BOT_POLL_INTERVAL` | Интервал опроса Telegram (сек) | `2.0` |
| `EXPORT_FORMAT` | `md`, `html` или `json` | `md` |

## Тесты

```bash
python -m pytest tests -v
```

## Структура

```
ai-trend-tracker/
├── main.py                # rich CLI
├── webapp.py              # Flask-дашборд
├── web/templates/         # HTML дашборда
├── web/static/            # CSS дашборда
├── src/
│   ├── config.py          # настройки (.env)
│   ├── logging_conf.py    # логирование
│   ├── parser.py          # парсинг RSS
│   ├── ai_analyzer.py     # ИИ-анализ (JSON)
│   ├── database.py        # SQLite
│   ├── report.py          # формирование отчётов
│   ├── notifier.py        # Telegram-уведомления
│   ├── bot.py             # интерактивный Telegram-бот
│   └── pipeline.py        # общий пайплайн
└── tests/                 # pytest
```
