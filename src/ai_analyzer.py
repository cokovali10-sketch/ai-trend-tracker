"""
Модуль ИИ-аналитики — отправляет текст статей в LLM и получает суммаризацию.
Поддерживает OpenAI и Google Gemini.
"""

from openai import OpenAI
import google.generativeai as genai

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


def analyze_with_openai(articles_text: str) -> str:
    """Отправляет текст статей в OpenAI и возвращает ответ."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Статьи для анализа:\n\n{articles_text}"},
        ],
        temperature=0.3,  # низкая температура — более фактологичный ответ
    )
    return response.choices[0].message.content


def analyze_with_gemini(articles_text: str) -> str:
    """Отправляет текст статей в Google Gemini и возвращает ответ."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(
        f"Статьи для анализа:\n\n{articles_text}",
    )
    return response.text


def analyze(articles_text: str) -> str:
    """
    Главная функция: выбирает нужного провайдера и возвращает результат.
    """
    if not articles_text.strip():
        return "Нет статей для анализа."

    if AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            return "[ОШИБКА] Не указан GEMINI_API_KEY в .env"
        return analyze_with_gemini(articles_text)

    # По умолчанию — OpenAI
    if not OPENAI_API_KEY:
        return "[ОШИБКА] Не указан OPENAI_API_KEY в .env"
    return analyze_with_openai(articles_text)
