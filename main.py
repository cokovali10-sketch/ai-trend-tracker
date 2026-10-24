"""
AI Trend Tracker — умный парсер + ИИ-аналитик ИТ-трендов.

Подкоманды:
  run        выполнить полный цикл анализа
  reports    список последних отчётов
  show N     показать отчёт #N
  stats      статистика по БД
  dashboard  запустить веб-дашборд
"""

import argparse
import sys
import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from src.config import settings
from src.logging_conf import setup_logging, get_logger
from src.pipeline import run_pipeline
from src.database import init_db, get_reports, get_report, get_stats
# --- константы вынесены FORGE refactor ---
CONST_60 = 60
CONST_80 = 80


log = get_logger("cli")
console = Console()


def _print_warnings() -> None:
    warns = settings.warnings()
    if warns:
        console.print(Panel(
            "\n".join(f"• {w}" for w in warns),
            title="⚠️  Конфигурация",
            border_style="yellow",
            box=box.ROUNDED,
        ))


def _print_header() -> None:
    console.print(Panel(
        "[bold cyan]AI Trend Tracker[/bold cyan]  ·  парсер + ИИ-аналитик ИТ-трендов",
        subtitle=f"провайдер: {settings.provider_name} · модель: {settings.gemini_model or settings.openai_model}",
        border_style="cyan",
        box=box.DOUBLE,
    ))


def cmd_run(args: argparse.Namespace) -> int:
    _print_header()
    _print_warnings()

    sources = args.sources or None
    max_articles = args.max_articles or settings.max_articles
    interval_min = args.every

    def _one_run() -> int:
        with console.status("[yellow]Выполняю анализ...[/yellow]", spinner="dots12"):
            result = run_pipeline(
                sources=sources,
                max_articles=max_articles,
                notify=not args.no_telegram,
                export=not args.no_export,
                export_format=args.export_format,
            )

        if not result.success:
            console.print(f"[red]❌ {result.error}[/red]")
            return 1

        if result.new == 0:
            console.print("[green]✅ Новых статей нет — выход.[/green]")
            return 0

        table = Table(box=box.ROUNDED, title="Результат запуска", title_style="bold cyan")
        table.add_column("Показатель", style="cyan")
        table.add_column("Значение")
        table.add_row("Всего статей", str(result.total))
        table.add_row("Новых обработано", f"[bold green]{result.new}[/bold green]")
        table.add_row("Отчёт в БД", f"#{result.report_id}" if result.report_id else "—")
        table.add_row("Telegram", "✅" if result.telegram_sent else "❌")
        table.add_row("Экспорт", result.exported_to or "—")
        table.add_row("Итог", result.summary[:CONST_80] + ("…" if len(result.summary) > CONST_80 else ""))
        console.print(table)
        console.print(f"\n💡 Показать отчёт: [bold]python main.py show {result.report_id}[/bold]")
        return 0

    if not args.loop:
        return _one_run()

    # Режим расписания: запускаемся каждые --every минут
    console.print(f"[cyan]🕒 Режим расписания: запуск каждые {interval_min} мин. Ctrl+C — остановка.[/cyan]")
    try:
        while True:
            _one_run()
            time.sleep(interval_min * CONST_60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Расписание остановлено.[/yellow]")
        return 0


def cmd_bot(args: argparse.Namespace) -> int:
    from src.bot import run_bot
    _print_header()
    try:
        run_bot(poll_interval=args.every)
    except KeyboardInterrupt:
        console.print("\n[yellow]Бот остановлен.[/yellow]")
    return 0


def cmd_reports(args: argparse.Namespace) -> int:
    _print_header()
    reports = get_reports(args.limit)
    if not reports:
        console.print("[yellow]Отчётов пока нет. Выполни: python main.py run[/yellow]")
        return 0

    table = Table(box=box.ROUNDED, title="История отчётов", title_style="bold cyan")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Дата", style="cyan")
    table.add_column("Новостей", justify="right")
    table.add_column("Модель")
    table.add_column("Вывод")
    for r in reports:
        overview = (r["overview"] or "")[:CONST_60]
        table.add_row(
            str(r["id"]),
            r["created_at"][:16].replace("T", " "),
            str(r["news_count"]),
            r["model"] or "—",
            overview + ("…" if len(overview) == CONST_60 else ""),
        )
    console.print(table)
    console.print("\n💡 Показать отчёт: [bold]python main.py show <ID>[/bold]")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    report = get_report(args.report_id)
    if not report:
        console.print(f"[red]Отчёт #{args.report_id} не найден[/red]")
        return 1
    console.print(Panel(
        f"Сформирован: {report['created_at']}  ·  Модель: {report['model']}  ·  Новостей: {report['news_count']}",
        title=f"Отчёт #{report['id']}",
        border_style="cyan",
        box=box.DOUBLE,
    ))
    console.print(report["content"])
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    _print_header()
    stats = get_stats()

    grid = Table(box=box.ROUNDED, title="Статистика", title_style="bold cyan", show_header=False)
    grid.add_column(style="cyan", width=22)
    grid.add_column()
    grid.add_row("Обработано статей всего", str(stats["processed"]))
    grid.add_row("Сегодня", str(stats["today"]))
    grid.add_row("Сформировано отчётов", str(stats["reports"]))
    grid.add_row("Последний отчёт", stats["last_report_at"] or "—")
    console.print(grid)

    if stats["models"]:
        mtable = Table(box=box.SIMPLE, title="Используемые модели", title_style="bold")
        mtable.add_column("Модель")
        mtable.add_column("Отчётов", justify="right")
        for m in stats["models"]:
            mtable.add_row(m["model"], str(m["count"]))
        console.print(mtable)

    if stats["last7"]:
        dtable = Table(box=box.SIMPLE, title="Активность за 7 дней", title_style="bold")
        dtable.add_column("День")
        dtable.add_column("Статей", justify="right")
        bar = lambda n: "█" * min(n, 30) + f" {n}"  # noqa: E731
        for d in stats["last7"]:
            dtable.add_row(d["day"], bar(d["count"]))
        console.print(dtable)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    _print_header()
    table = Table(box=box.ROUNDED, title="Конфигурация", title_style="bold cyan", show_header=False)
    table.add_column("Параметр", style="cyan", width=20)
    table.add_column("Значение")
    for key, value in settings.as_table().items():
        table.add_row(key, value)
    console.print(table)

    sec = Table(box=box.SIMPLE, title="Секреты (замаскированы)", title_style="bold")
    sec.add_column("Переменная")
    sec.add_column("Значение")
    for key, value in settings.secrets_masked().items():
        sec.add_row(key, value)
    console.print(sec)

    _print_warnings()
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    init_db()
    console.print("[cyan]Запускаю веб-дашборд: [bold]http://127.0.0.1:5000[/bold][/cyan]")
    console.print("[dim]Остановка: Ctrl+C[/dim]")
    from webapp import app
    app.run(host=args.host, port=args.port, debug=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-trend-tracker",
        description="Парсер + ИИ-аналитик ИТ-трендов с Telegram-уведомлениями и веб-дашбордом.",
    )
    parser.add_argument("--version", action="version", version="AI Trend Tracker 2.0")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="полный цикл анализа")
    p_run.add_argument("--sources", nargs="*", help="RSS-источники (перекроют .env)")
    p_run.add_argument("--max-articles", type=int, help="макс. статей на источник")
    p_run.add_argument("--no-telegram", action="store_true", help="не отправлять в Telegram")
    p_run.add_argument("--no-export", action="store_true", help="не экспортировать отчёт в файл")
    p_run.add_argument("--export-format", choices=["md", "html", "json"], default=settings.export_format,
                       help="формат экспорта отчёта")
    p_run.add_argument("--loop", action="store_true", help="работать по расписанию (бесконечно)")
    p_run.add_argument("--every", type=float, default=settings.run_interval_min,
                       help="интервал запусков в минутах (для --loop)")
    p_run.set_defaults(func=cmd_run)

    p_bot = sub.add_parser("bot", help="интерактивный Telegram-бот (/today, /stats, /recent)")
    p_bot.add_argument("--every", type=float, default=settings.bot_poll_interval,
                       help="интервал опроса Telegram, сек")
    p_bot.set_defaults(func=cmd_bot)

    p_reports = sub.add_parser("reports", help="список последних отчётов")
    p_reports.add_argument("--limit", type=int, default=10)
    p_reports.set_defaults(func=cmd_reports)

    p_show = sub.add_parser("show", help="показать отчёт по id")
    p_show.add_argument("report_id", type=int)
    p_show.set_defaults(func=cmd_show)

    p_stats = sub.add_parser("stats", help="статистика по БД")
    p_stats.set_defaults(func=cmd_stats)

    p_config = sub.add_parser("config", help="показать текущую конфигурацию")
    p_config.set_defaults(func=cmd_config)

    p_dash = sub.add_parser("dashboard", help="запустить веб-дашборд")
    p_dash.add_argument("--host", default="127.0.0.1")
    p_dash.add_argument("--port", type=int, default=5000)
    p_dash.set_defaults(func=cmd_dashboard)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    setup_logging()
    init_db()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
