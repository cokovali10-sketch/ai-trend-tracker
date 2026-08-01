"""Тесты форматирования отчётов."""

from src.ai_analyzer import AnalysisResult, Trend
from src.report import build_telegram_text, build_markdown, build_html
from src.notifier import _split_text as _split_telegram


def _result():
    return AnalysisResult(
        trends=[
            Trend(title="AI <в разработке>", summary="Суть & факты",
                  importance="Важно", category="AI", sentiment="positive",
                  link="https://x.ru/a?b=1&c=2"),
        ],
        overview="Общий вывод",
        raw="{}",
        model="test-model",
    )


def test_telegram_text_escapes_html():
    text = build_telegram_text(_result())
    assert "&lt;в разработке&gt;" in text      # < > экранированы
    assert "&amp; факты" in text                # & экранирован
    assert "<b>1. AI &lt;в разработке&gt;</b>" in text


def test_telegram_text_contains_link():
    text = build_telegram_text(_result())
    assert "href='https://x.ru/a?b=1&amp;c=2'" in text


def test_telegram_text_empty_trends():
    r = AnalysisResult(trends=[], overview="Пусто", raw="{}", model="m")
    assert "Пусто" in build_telegram_text(r)


def test_split_telegram_chunks():
    assert _split_telegram("короткий текст") == ["короткий текст"]
    long = "\n\n".join(f"Абзац {i} " + "x" * 100 for i in range(100))
    chunks = _split_telegram(long)
    assert len(chunks) > 1
    assert all(len(c) <= 4096 for c in chunks)
    assert "Абзац 0" in chunks[0]


def test_build_markdown_contains_fields():
    md = build_markdown(_result())
    assert "AI <в разработке>" in md
    assert "[Источник](https://x.ru/a?b=1&c=2)" in md


def test_build_html_contains_escaped_title():
    html = build_html(_result())
    assert "AI &lt;в разработке&gt;" in html
    assert "<html" in html
