"""Тесты парсинга JSON-ответов ИИ и нормализации полей."""

from src.ai_analyzer import _parse_json, _to_result, _normalize_category, _normalize_sentiment


def test_parse_json_plain():
    assert _parse_json('{"trends": []}') == {"trends": []}


def test_parse_json_markdown_fence():
    raw = '```json\n{"trends": [], "overview": "OK"}\n```'
    assert _parse_json(raw) == {"trends": [], "overview": "OK"}


def test_parse_json_invalid_returns_none():
    assert _parse_json("это не json") is None


def test_normalize_category_known():
    assert _normalize_category("AI") == "AI"
    assert _normalize_category("security") == "Security"
    assert _normalize_category("  development  ") == "Development"


def test_normalize_category_unknown_to_other():
    assert _normalize_category("космос") == "Other"
    assert _normalize_category("") == "Other"


def test_normalize_sentiment():
    assert _normalize_sentiment("POSITIVE") == "positive"
    assert _normalize_sentiment("странно") == "neutral"
    assert _normalize_sentiment("") == "neutral"


def test_to_result_builds_trends():
    raw = ('{"trends": [{"title": "Тренд", "summary": "Суть", '
           '"category": "security", "sentiment": "negative", "link": "https://x.ru"}], '
           '"overview": "День"}')
    result = _to_result(raw, "test-model")
    assert len(result.trends) == 1
    t = result.trends[0]
    assert t.category == "Security"
    assert t.sentiment == "negative"
    assert result.overview == "День"
    assert result.model == "test-model"


def test_to_result_skips_empty_titles():
    raw = '{"trends": [{"title": "", "summary": "x"}, {"title": "Реальный", "summary": "y"}]}'
    result = _to_result(raw, "m")
    assert len(result.trends) == 1
    assert result.trends[0].title == "Реальный"


def test_to_result_fallback_on_non_json():
    result = _to_result("просто текст", "m")
    assert result.is_empty
    assert result.overview == "просто текст"
