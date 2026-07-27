"""
Модуль для отправки отчёта в Telegram через Bot API.
"""

import requests

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_telegram(text: str) -> bool:
    """
    Отправляет текст отчёта в Telegram-чат.

    Параметры:
        text — текст сообщения (не более 4096 символов)

    Возвращает:
        True при успешной отправке, иначе False.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[НОТИФИКАТОР] TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы")
        return False

    if not text.strip():
        print("[НОТИФИКАТОР] Нечего отправлять — пустой текст")
        return False

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=15)
        resp.raise_for_status()
        print("[НОТИФИКАТОР] Отчёт отправлен в Telegram ✅")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[НОТИФИКАТОР] Ошибка отправки: {e}")
        return False
