"""Тесты пайплайна: обработка пустого результата ИИ и флага экспорта."""

from src.ai_analyzer import AnalysisResult
from src.parser import Article
from src import pipeline
# --- константы вынесены FORGE refactor ---
CONST_42 = 42



class _FakeResult:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _patch_env(monkeypatch, send_spy=None):
    monkeypatch.setattr(pipeline, "init_db", lambda: None)
    monkeypatch.setattr(pipeline, "is_processed", lambda link: False)
    monkeypatch.setattr(pipeline, "save_article", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "save_report", lambda result, n: CONST_42)
    monkeypatch.setattr(pipeline, "export_report", lambda result, fmt="md": None)
    monkeypatch.setattr(pipeline, "build_telegram_text", lambda result: "text")
    if send_spy is None:
        send_spy = []
    monkeypatch.setattr(pipeline, "send_telegram", lambda text: (send_spy.append(text), True)[1])
    return send_spy


def test_pipeline_empty_ai_result_skips_telegram(monkeypatch):
    spy = _patch_env(monkeypatch)
    articles = [Article(title="A", link="https://x.ru/1", summary="", published="")]
    monkeypatch.setattr(pipeline, "fetch_all_sources", lambda s, m: articles)
    monkeypatch.setattr(pipeline, "analyze", lambda text: AnalysisResult(
        trends=[], overview="", raw="{}", model="m"))

    result = pipeline.run_pipeline(notify=True)
    assert result.success
    assert result.new == 1
    assert result.report_id == CONST_42
    assert spy == []  # пустой результат не отправляем в Telegram


def test_pipeline_sends_telegram_on_trends(monkeypatch):
    spy = _patch_env(monkeypatch)
    articles = [Article(title="A", link="https://x.ru/1", summary="", published="")]
    monkeypatch.setattr(pipeline, "fetch_all_sources", lambda s, m: articles)
    monkeypatch.setattr(pipeline, "analyze", lambda text: AnalysisResult(
        trends=[], overview="День прошёл", raw="{}", model="m"))

    result = pipeline.run_pipeline(notify=True)
    assert result.success
    assert spy == ["text"]


def test_pipeline_no_new_articles(monkeypatch):
    _patch_env(monkeypatch)
    articles = [Article(title="A", link="https://x.ru/1", summary="", published="")]
    monkeypatch.setattr(pipeline, "fetch_all_sources", lambda s, m: articles)
    monkeypatch.setattr(pipeline, "is_processed", lambda link: True)

    result = pipeline.run_pipeline(notify=True)
    assert result.success
    assert result.new == 0
    assert result.report_id is None
