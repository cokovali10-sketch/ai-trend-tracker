"""
Модуль ИИ-аналитики — отправляет текст статей в LLM и получает суммаризацию.
Поддерживает Gemini (по умолчанию) и OpenAI.
"""

import time
from openai import OpenAI
from google import genai
from google.genai import types, errors as genai_errors

from src.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    AI_PROVIDER,
)

# --- Промпт для ИИ-аналитика ---
SYSTEM_PROMPT = """
Ты — профессиональный ИТ-аналитик с многолетним опытом.
Ниже приведены сырые тексты свежих статей с IT-новостного портала.

Твоя задача:
1. Внимательно прочитай каждую статью.
2. Отфильтруй спам, рекламные анонсы, пустые и малозначимые заметки.
3. Выбери ТОП-3 самых важных новости или тренда за сегодня.
4. По каждой новости напиши:
   - **Заголовок** — сформулируй ёмко и понятно.
   - **Суть** — 2-3 предложения, что произошло и о чём речь.
   - **Почему это важно** — 1 предложение о влиянии на индустрию.

Формат ответа (строго):
1. **[Заголовок новости]**
   Суть: ...
   Почему это важно: ...

2. **[Заголовок новости]**
   Суть: ...
   Почему это важно: ...

3. **[Заголовок новости]**
   Суть: ...
   Почему это важно: ...

В конце можешь добавить раздел "📈 Краткий вывод:" — одно предложение с общей картиной дня.
"""

# Максимальное количество повторов при превышении квоты
_MAX_RETRIES = 3
_RETRY_DELAY = 10  # секунд между повторами


def _call_with_retry(fn, *args, **kwargs):
    """Вызывает fn с повторными попытками при ошибках квоты/таймаута."""
    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except genai_errors.ClientError as e:
            last_error = e
            if attempt < _MAX_RETRIES and e.code == 429:
                wait = _RETRY_DELAY * (2 ** (attempt - 1))
                print(f"⚠️  Квота Gemini: повтор через {wait}с (попытка {attempt}/{_MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise
        except genai_errors.APIError as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_DELAY * (2 ** (attempt - 1))
                print(f"⚠️  Ошибка API Gemini: {e}, повтор через {wait}с...")
                time.sleep(wait)
    raise last_error


def analyze_with_openai(articles_text: str) -> str:
    """Отправляет текст статей в OpenAI и возвращает ответ."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Статьи для анализа:\n\n{articles_text}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def analyze_with_gemini(articles_text: str) -> str:
    """Отправляет текст статей в Google Gemini (новый SDK google.genai)."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    def _do_request():
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"Статьи для анализа:\n\n{articles_text}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        return response.text

    return _call_with_retry(_do_request)


def analyze(articles_text: str) -> str:
    """
    Главная функция: выбирает нужного провайдера и возвращает результат.
    """
    if not articles_text.strip():
        return "Нет статей для анализа."

    if AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            return "[ОШИБКА] Не указан GEMINI_API_KEY в .env"
        try:
            return analyze_with_gemini(articles_text)
        except genai_errors.ClientError:
            return ("[ОШИБКА] Исчерпана квота Gemini API. "
                    "Попробуй другую модель (например, gemini-2.0-flash-lite) "
                    "или подключи платёжный аккаунт: https://aistudio.google.com/apikey")

    if not OPENAI_API_KEY:
        return "[ОШИБКА] Не указан OPENAI_API_KEY в .env"
    return analyze_with_openai(articles_text)
