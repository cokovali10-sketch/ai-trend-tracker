"""
Модуль отправки отчётов в Telegram через Bot API.
"""

import time

import requests

from src.config import settings
from src.logging_conf import get_logger

log = get_logger("notifier")

_MAX_LEN = 4096  # лимит одного сообщения Telegram
_MAX_RETRIES = 3  # повтор при 429 (лимит частоты)


def _split_text(text: str, limit: int = _MAX_LEN) -> list[str]:
    """Разбивает длинный текст на куски по границам абзацев."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for para in text.split("\n\n"):
        if len(current) + len(para) + 2 > limit:
            chunks.append(current)
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


def _send_chunk(chat_id: str, text: str, parse_mode: str) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 429:
                # Telegram просит подождать — соблюдаем, затем повторяем
                wait = int(resp.json().get("parameters", {}).get("retry_after", 2)) + 1
                log.warning("Telegram 429 (chat %s): повтор через %ds (попытка %d/%d)",
                            chat_id, wait, attempt, _MAX_RETRIES)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            body = getattr(e.response, "text", "")[:300] if hasattr(e, "response") else ""
            log.error("Ошибка отправки в Telegram (chat %s): %s %s", chat_id, e, body)
            if attempt < _MAX_RETRIES:
                time.sleep(2 * attempt)
    return False


def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    """Отправляет текст всем настроенным чатам. Возвращает True, если все ушли."""
    if not settings.telegram_enabled:
        log.warning("Telegram не настроен — сообщение не отправлено")
        return False
    if not text.strip():
        log.warning("Пустой текст — сообщение не отправлено")
        return False

    ok = True
    for chat_id in settings.telegram_chat_ids:
        for chunk in _split_text(text):
            if not _send_chunk(chat_id, chunk, parse_mode):
                ok = False
    if ok:
        log.info("Отчёт отправлен в Telegram (%d чатов)", len(settings.telegram_chat_ids))
    return ok
