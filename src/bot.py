"""
Интерактивный Telegram-бот — отвечает на команды в чате.

Запуск:
    python main.py bot

Команды:
    /today   запустить анализ и прислать отчёт
    /stats   статистика по БД
    /recent  последние 5 отчётов
    /model   показать текущую модель ИИ
    /help    справка
"""

import threading
import time

import requests

from src.config import settings
from src.logging_conf import get_logger
from src.pipeline import run_pipeline
from src.database import get_stats, get_reports, get_report
from src.report import build_telegram_text

log = get_logger("bot")

HELP_TEXT = """<b>🤖 AI Trend Tracker Bot</b>

/today — запустить анализ и прислать отчёт
/stats — статистика по БД
/recent — последние 5 отчётов
/model — текущая модель ИИ
/help — это сообщение"""


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"


def _send(chat_id: str, text: str, parse_mode: str = "HTML") -> None:
    try:
        resp = requests.post(
            _api_url("sendMessage"),
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.error("Ошибка отправки в чат %s: %s", chat_id, e)


def _is_allowed(chat_id: str) -> bool:
    """Разрешаем общаться только настроенным чатам."""
    return not settings.telegram_chat_ids or chat_id in settings.telegram_chat_ids


def _cmd_today(chat_id: str) -> None:
    _send(chat_id, "⏳ Запускаю анализ…")
    result = run_pipeline(notify=False, export=False)
    if not result.success:
        _send(chat_id, f"❌ {result.error}")
    elif result.new == 0:
        _send(chat_id, "✅ Новых статей нет.")
    else:
        rep = get_report(result.report_id)
        _send(chat_id, rep["content"] if rep else f"✅ Отчёт #{result.report_id} создан.")


def _handle(chat_id: str, text: str) -> None:
    """Обрабатывает одну команду."""
    cmd = (text or "").strip().split()[0].lower() if (text or "").strip() else "/help"

    if cmd == "/today":
        # Анализ долгий — выполняем в фоне, чтобы бот продолжал отвечать
        threading.Thread(target=_cmd_today, args=(chat_id,), daemon=True).start()

    elif cmd == "/stats":
        s = get_stats()
        _send(chat_id,
              "<b>📊 Статистика</b>\n"
              f"Обработано статей: {s['processed']}\n"
              f"Сегодня: {s['today']}\n"
              f"Отчётов: {s['reports']}\n"
              f"Последний отчёт: {s['last_report_at'] or '—'}")

    elif cmd == "/recent":
        reps = get_reports(5)
        if not reps:
            _send(chat_id, "Отчётов пока нет. Отправь /today.")
            return
        lines = ["<b>Последние отчёты:</b>"]
        for r in reps:
            overview = (r["overview"] or "")[:50]
            lines.append(f"#{r['id']} · {r['created_at'][:16].replace('T', ' ')} — {overview}")
        _send(chat_id, "\n".join(lines))

    elif cmd == "/model":
        _send(chat_id, f"🧠 Провайдер: <b>{settings.provider_name}</b>\nМодель: <code>{settings.model_name}</code>")

    else:
        _send(chat_id, HELP_TEXT)


def run_bot(poll_interval: float = 2.0) -> None:
    """Длинный опрос getUpdates и обработка команд."""
    if not settings.telegram_enabled:
        log.error("Telegram не настроен — бот не может работать")
        return

    log.info("Бот запущен. Нажми Ctrl+C для остановки.")
    offset = None

    while True:
        try:
            resp = requests.get(
                _api_url("getUpdates"),
                params={"timeout": 30, "offset": offset},
                timeout=35,
            )
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("channel_post")
                if not message:
                    continue
                chat_id = str(message["chat"]["id"])
                if not _is_allowed(chat_id):
                    log.info("Игнорирую чужой чат: %s", chat_id)
                    continue
                text = message.get("text", "")
                if text.startswith("/"):
                    log.info("Команда от %s: %s", chat_id, text.split()[0])
                    _handle(chat_id, text)
        except requests.exceptions.RequestException as e:
            log.error("Ошибка long-polling: %s", e)
            time.sleep(5)
        except Exception as e:  # noqa: BLE001
            log.error("Непредвиденная ошибка: %s", e)
            time.sleep(5)
        time.sleep(poll_interval)
