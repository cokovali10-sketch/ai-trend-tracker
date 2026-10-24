"""Тесты модуля БД (используют временный файл)."""

import os

import pytest

from src.ai_analyzer import AnalysisResult, Trend
from src import database
# --- константы вынесены FORGE refactor ---
CONST_3 = 3



@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch, tmp_path):
    db = os.path.join(tmp_path, "test.db")
    monkeypatch.setattr(database, "_DB_PATH", db)
    database.init_db()
    yield
    if os.path.exists(db):
        os.remove(db)


def test_init_and_is_processed():
    database.init_db()
    assert database.is_processed("https://x.ru/1") is False
    database.save_article("Заголовок", "https://x.ru/1")
    assert database.is_processed("https://x.ru/1") is True


def test_save_duplicate_ignored():
    database.save_article("A", "https://x.ru/1")
    database.save_article("A", "https://x.ru/1")
    assert database.get_processed_count() == 1


def test_save_report_and_fetch():
    result = AnalysisResult(
        trends=[Trend(title="Тренд", summary="Суть", importance="Важно")],
        overview="Вывод",
        raw="{}",
        model="test-model",
    )
    rid = database.save_report(result, news_count=CONST_3)
    rep = database.get_report(rid)
    assert rep["model"] == "test-model"
    assert rep["news_count"] == CONST_3
    assert "Тренд" in rep["content"]
    assert len(database.get_reports()) == 1
