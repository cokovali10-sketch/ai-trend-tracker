"""
Общий пайплайн анализа — используется и в CLI, и в веб-дашборде.

  Парсинг → фильтр дубликатов → ИИ-анализ → сохранение в БД → Telegram → экспорт
"""

from dataclasses import dataclass, asdict
from typing import Optional

from src.config import settings
from src.logging_conf import get_logger
from src.parser import fetch_all_sources, articles_to_text
from src.ai_analyzer import analyze, AnalysisResult, QuotaExhaustedError, MissingApiKeyError
from src.database import init_db, is_processed, save_article, save_report, get_processed_count
from src.notifier import send_telegram
from src.report import build_telegram_text, export_report

log = get_logger("pipeline")


@dataclass
class PipelineResult:
    """Итог одного прогона пайплайна."""
    total: int = 0
    new: int = 0
    success: bool = False
    error: str = ""
    report_id: Optional[int] = None
    telegram_sent: bool = False
    exported_to: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def run_pipeline(
    sources: Optional[list[str]] = None,
    max_articles: Optional[int] = None,
    notify: Optional[bool] = None,
    export: Optional[bool] = None,
    export_format: Optional[str] = None,
) -> PipelineResult:
    """Выполняет полный цикл: парсинг → анализ → БД → Telegram → экспорт."""
    sources = sources or settings.rss_sources
    max_articles = max_articles or settings.max_articles
    notify = settings.notify_enabled if notify is None else notify
    export = True if export is None else export
    export_format = export_format or settings.export_format

    init_db()
    log.info("Начинаем анализ: %d источников, до %d статей", len(sources), max_articles)

    articles = fetch_all_sources(sources, max_articles)
    if not articles:
        return PipelineResult(success=False, error="Не удалось загрузить статьи ни из одного источника")

    new_articles = [a for a in articles if not is_processed(a.link)]
    if not new_articles:
        log.info("Новых статей нет (все %d уже обработаны)", len(articles))
        return PipelineResult(total=len(articles), new=0, success=True, summary="Новых статей нет")

    log.info("Новых статей: %d из %d", len(new_articles), len(articles))
    text = articles_to_text(new_articles)

    try:
        result: AnalysisResult = analyze(text)
    except QuotaExhaustedError as e:
        log.error("Квота исчерпана: %s", e)
        return PipelineResult(total=len(articles), new=len(new_articles), success=False, error=str(e))
    except MissingApiKeyError as e:
        log.error("Нет ключа: %s", e)
        return PipelineResult(total=len(articles), new=len(new_articles), success=False, error=str(e))

    # Сохраняем только после успешного анализа
    for a in new_articles:
        save_article(a.title, a.link, a.source, a.published)
    report_id = save_report(result, len(new_articles))
    log.info("Отчёт #%d сохранён в БД (модель: %s)", report_id, result.model)

    # Пустой результат ИИ без вывода не рассылаем в Telegram — это не информативно.
    # Если есть overview (например, модель вернула текст без JSON) — отправляем.
    has_content = (not result.is_empty) or bool(result.overview)
    telegram_sent = send_telegram(build_telegram_text(result)) if (notify and has_content) else False
    exported = export_report(result, fmt=export_format) if export else None

    return PipelineResult(
        total=len(articles),
        new=len(new_articles),
        success=True,
        report_id=report_id,
        telegram_sent=telegram_sent,
        exported_to=exported,
        summary=result.overview,
    )
