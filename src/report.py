"""
Модуль формирования отчётов — тексты для Telegram, файлов и экспорта.
"""

import json
import os
from datetime import datetime
from html import escape
from typing import Optional

from src.ai_analyzer import AnalysisResult
from src.config import settings, path_for
from src.logging_conf import get_logger

log = get_logger("report")

_SENTIMENT_EMOJI = {
    "positive": "🟢",
    "negative": "🔴",
    "neutral": "⚪",
}

_CATEGORY_EMOJI = {
    "AI": "🤖",
    "Security": "🛡️",
    "Business": "💼",
    "Legal": "⚖️",
    "Hardware": "🔩",
    "Development": "💻",
    "Other": "📰",
}


def _sentiment_emoji(sentiment: str) -> str:
    return _SENTIMENT_EMOJI.get((sentiment or "neutral").lower(), "⚪")


def _category_emoji(category: str) -> str:
    return _CATEGORY_EMOJI.get(category.title(), "📰")


def build_telegram_text(result: AnalysisResult) -> str:
    """Форматирует результат для Telegram (HTML parse_mode)."""
    lines = ["<b>📊 ИТ-тренды на сегодня</b>", ""]
    for i, t in enumerate(result.trends, 1):
        lines.append(f"<b>{i}. {escape(t.title)}</b>")
        lines.append(
            f"{_category_emoji(t.category)} {escape(t.category)} · "
            f"{_sentiment_emoji(t.sentiment)} {escape(t.sentiment)}"
        )
        lines.append(escape(t.summary))
        if t.importance:
            lines.append(f"💡 <i>{escape(t.importance)}</i>")
        if t.link:
            lines.append(f"🔗 <a href='{escape(t.link)}'>Источник</a>")
        lines.append("")
    if result.overview:
        lines.append(f"📈 <i>Вывод:</i> {escape(result.overview)}")
    if result.model:
        lines.append(f"🧠 Модель: {escape(result.model)}")
    return "\n".join(lines)


def build_markdown(result: AnalysisResult) -> str:
    """Markdown-отчёт для экспорта в файл."""
    lines = ["# 📊 ИТ-тренды на сегодня", ""]
    lines.append(f"_Сформировано: {datetime.now():%Y-%m-%d %H:%M}_")
    if result.model:
        lines.append(f"_Модель: {result.model}_")
    lines.append("")
    for i, t in enumerate(result.trends, 1):
        lines.append(f"## {i}. {t.title}")
        lines.append(f"**Категория:** {t.category} · **Эмоция:** {t.sentiment}")
        lines.append("")
        lines.append(t.summary)
        lines.append("")
        if t.importance:
            lines.append(f"> 💡 {t.importance}")
        if t.link:
            lines.append(f"> 🔗 [Источник]({t.link})")
        lines.append("")
        lines.append("---")
        lines.append("")
    if result.overview:
        lines.append(f"## 📈 Краткий вывод")
        lines.append("")
        lines.append(result.overview)
    return "\n".join(lines)


def build_html(result: AnalysisResult) -> str:
    """Автономный HTML-отчёт (тёмная тема) для просмотра в браузере."""
    def esc(text: str) -> str:
        return escape(text or "")

    cards = "".join(
        f"""
        <div class="trend">
          <h2>{i}. {esc(t.title)}</h2>
          <div class="meta">{esc(t.category)} · {esc(t.sentiment)}</div>
          <p>{esc(t.summary)}</p>
          {f"<p class='imp'>💡 {esc(t.importance)}</p>" if t.importance else ""}
          {f"<a class='src' href='{esc(t.link)}'>Источник</a>" if t.link else ""}
        </div>"""
        for i, t in enumerate(result.trends, 1)
    )
    overview = f"<h2>📈 Краткий вывод</h2><p>{esc(result.overview)}</p>" if result.overview else ""
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>ИТ-тренды</title>
<style>
  body {{ background:#0f1117; color:#e6e8ef; font-family:Segoe UI,sans-serif; max-width:760px; margin:40px auto; padding:0 20px; }}
  h1 {{ color:#4cc9f0; }} .meta {{ color:#8b90a3; font-size:13px; margin:4px 0 10px; }}
  .trend {{ background:#1c2030; border:1px solid #2a2f42; border-radius:12px; padding:18px 20px; margin:16px 0; }}
  .imp {{ color:#f4d35e; }} .src {{ color:#4cc9f0; }} p {{ line-height:1.5; }}
</style></head>
<body>
<h1>📊 ИТ-тренды на сегодня</h1>
<p class="meta">Сформировано: {datetime.now():%Y-%m-%d %H:%M} · Модель: {esc(result.model) or 'AI'}</p>
{cards}{overview}
</body></html>"""


def export_report(result: AnalysisResult, fmt: str = "md") -> Optional[str]:
    """Сохраняет отчёт в reports_dir. fmt: md | html. Возвращает путь или None."""
    try:
        os.makedirs(path_for(settings.reports_dir), exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(path_for(settings.reports_dir), f"report_{stamp}.{fmt}")
        if fmt == "html":
            content = build_html(result)
        elif fmt == "json":
            content = json.dumps({"trends": [vars(t) for t in result.trends], "overview": result.overview},
                                 ensure_ascii=False, indent=2)
        else:
            content = build_markdown(result)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        log.info("Отчёт сохранён: %s", file_path)
        return file_path
    except OSError as e:
        log.error("Не удалось сохранить отчёт: %s", e)
        return None
