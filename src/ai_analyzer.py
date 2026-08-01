"""
Модуль ИИ-аналитики — отправляет текст статей в LLM и получает структурированную сводку.

Поддерживает Gemini (по умолчанию) и OpenAI. Модель возвращает JSON:
  {
    "trends": [{"title", "summary", "importance", "category", "sentiment", "link"}],
    "overview": "..."
  }
"""

import json
import re
import time
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from google import genai
from google.genai import types, errors as genai_errors

from src.config import settings
from src.logging_conf import get_logger

log = get_logger("ai")


class QuotaExhaustedError(Exception):
    """Квота ИИ исчерпана — не удалось получить ответ ни от одной модели."""


class MissingApiKeyError(Exception):
    """Не задан API-ключ для выбранного провайдера."""


@dataclass
class Trend:
    """Одна новость/тренд из сводки."""
    title: str
    summary: str
    importance: str = ""
    category: str = "Other"
    sentiment: str = "neutral"
    link: str = ""


@dataclass
class AnalysisResult:
    """Результат анализа: список трендов + общий вывод."""
    trends: list[Trend]
    overview: str
    raw: str
    model: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.trends


SYSTEM_PROMPT = """Ты — профессиональный ИТ-аналитик с многолетним опытом.
Ниже приведены сырые тексты свежих статей с IT-новостных порталов.

Твоя задача:
1. Внимательно прочитай каждую статью.
2. Отфильтруй спам, рекламные анонсы, пустые и малозначимые заметки.
3. Выбери ТОП-3 самых важных новости или тренда за сегодня.
4. Для каждой новости заполни поля.

Ответь ТОЛЬКО валидным JSON без markdown-обёрток и без пояснений, строго в формате:
{
  "trends": [
    {
      "title": "Ёмкий заголовок новости",
      "summary": "Суть в 2-3 предложениях",
      "importance": "Почему это важно — 1 предложение о влиянии на индустрию",
      "category": "AI | Security | Business | Legal | Hardware | Development | Other",
      "sentiment": "positive | negative | neutral",
      "link": "Прямая ссылка на статью-источник (скопируй её из блока 'Ссылка:' статьи), или пустая строка"
    }
  ],
  "overview": "Одно предложение — общая картина дня"
}

Все текстовые поля пиши на русском языке. Категорию и sentiment — строго по списку."""

# Запасные модели — если основная исчерпала квоту (у каждой модели квота своя).
# Модели 2.x для новых аккаунтов недоступны (404), поэтому только 3.x.
_GEMINI_FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]

_ALLOWED_CATEGORIES = {"ai", "security", "business", "legal", "hardware", "development", "other"}
_ALLOWED_SENTIMENTS = {"positive", "negative", "neutral"}

_MAX_RETRIES = 3
_RETRY_DELAY = 10  # секунд между повторами


def _gemini_response_schema() -> "types.Schema":
    """Схема ответа — модель обязана вернуть строго валидный JSON нужной структуры."""
    trend = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(type=types.Type.STRING, description="Ёмкий заголовок новости"),
            "summary": types.Schema(type=types.Type.STRING, description="Суть в 2-3 предложениях"),
            "importance": types.Schema(type=types.Type.STRING, description="Почему это важно"),
            "category": types.Schema(type=types.Type.STRING, description="AI | Security | Business | Legal | Hardware | Development | Other"),
            "sentiment": types.Schema(type=types.Type.STRING, description="positive | negative | neutral"),
            "link": types.Schema(type=types.Type.STRING, description="Прямая ссылка на статью-источник"),
        },
        required=["title", "summary"],
    )
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "trends": types.Schema(type=types.Type.ARRAY, items=trend),
            "overview": types.Schema(type=types.Type.STRING, description="Общая картина дня"),
        },
        required=["trends", "overview"],
    )


def _build_model_chain() -> list[str]:
    """Строит цепочку моделей: основная из .env + запасные."""
    chain = [settings.gemini_model]
    for model in _GEMINI_FALLBACK_MODELS:
        if model not in chain:
            chain.append(model)
    return chain


def _call_with_retry(fn, *args, **kwargs):
    """Вызывает fn с повторными попытками при ошибках квоты/таймаута."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except genai_errors.ClientError as e:
            if attempt < _MAX_RETRIES and e.code == 429:
                wait = _RETRY_DELAY * (2 ** (attempt - 1))
                log.warning("Квота: повтор через %ds (попытка %d/%d)", wait, attempt, _MAX_RETRIES)
                time.sleep(wait)
            else:
                raise
        except genai_errors.APIError as e:
            if attempt < _MAX_RETRIES:
                wait = _RETRY_DELAY * (2 ** (attempt - 1))
                log.warning("Ошибка API: %s. Повтор через %ds", e, wait)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Не удалось получить ответ после повторных попыток")


def analyze_with_openai(articles_text: str) -> tuple[str, str]:
    """Отправляет текст в OpenAI. Возвращает (raw_json, model)."""
    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Статьи для анализа:\n\n{articles_text}"},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content, model


def analyze_with_gemini(articles_text: str) -> tuple[str, str]:
    """Отправляет текст в Gemini с ротацией моделей. Возвращает (raw_json, model)."""
    client = genai.Client(api_key=settings.gemini_api_key)
    chain = _build_model_chain()

    for model in chain:
        log.info("Пробуем модель: %s", model)

        def _do_request(m=model):
            response = client.models.generate_content(
                model=m,
                contents=f"Статьи для анализа:\n\n{articles_text}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_gemini_response_schema(),
                    temperature=0.3,
                ),
            )
            return response.text

        try:
            return _call_with_retry(_do_request), model
        except genai_errors.ClientError:
            log.warning("Модель %s недоступна по квоте, пробуем следующую", model)

    raise QuotaExhaustedError(
        "Квота Gemini исчерпана у всех моделей. "
        "Подключи платёжный аккаунт или используй другой API-ключ: "
        "https://aistudio.google.com/apikey"
    )


def _parse_json(raw: str) -> Optional[dict]:
    """Извлекает JSON из ответа модели (убирает markdown-обёртки при наличии)."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_category(value: str) -> str:
    """Приводит категорию к известному списку, иначе Other."""
    v = (value or "other").strip().lower()
    if v not in _ALLOWED_CATEGORIES:
        return "Other"
    # Канонические написания (title() искажает аббревиатуры: AI → Ai)
    return {"ai": "AI", "security": "Security", "business": "Business",
            "legal": "Legal", "hardware": "Hardware", "development": "Development",
            "other": "Other"}[v]


def _normalize_sentiment(value: str) -> str:
    v = (value or "neutral").strip().lower()
    return v if v in _ALLOWED_SENTIMENTS else "neutral"


def _to_result(raw: str, model: str) -> AnalysisResult:
    """Преобразует сырой ответ модели в AnalysisResult."""
    data = _parse_json(raw)
    if data:
        trends = []
        for item in data.get("trends", []):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            trends.append(Trend(
                title=title,
                summary=str(item.get("summary", "")).strip(),
                importance=str(item.get("importance", "")).strip(),
                category=_normalize_category(str(item.get("category", ""))),
                sentiment=_normalize_sentiment(str(item.get("sentiment", ""))),
                link=str(item.get("link", "")).strip(),
            ))
        if trends:
            return AnalysisResult(
                trends=trends,
                overview=str(data.get("overview", "")).strip(),
                raw=raw,
                model=model,
            )
    # Фолбэк: модель вернула текст без JSON
    return AnalysisResult(trends=[], overview=raw.strip(), raw=raw, model=model)


def analyze(articles_text: str) -> AnalysisResult:
    """Главная функция анализа. Возвращает AnalysisResult.

    Исключения: MissingApiKeyError, QuotaExhaustedError.
    """
    if not articles_text.strip():
        return AnalysisResult(trends=[], overview="Нет статей для анализа.", raw="")

    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key:
            raise MissingApiKeyError("Не указан GEMINI_API_KEY в .env")
        raw, model = analyze_with_gemini(articles_text)
    else:
        if not settings.openai_api_key:
            raise MissingApiKeyError("Не указан OPENAI_API_KEY в .env")
        raw, model = analyze_with_openai(articles_text)

    return _to_result(raw, model)
