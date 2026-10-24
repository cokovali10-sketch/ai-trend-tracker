"""
Веб-дашборд AI Trend Tracker (Flask).

Запуск:
    python webapp.py            # или: python main.py dashboard
    → http://127.0.0.1:5000
"""

import json
import os
import threading
import time

from flask import Flask, jsonify, render_template

from src.config import settings
from src.logging_conf import setup_logging, get_logger
from src.database import init_db, get_stats, get_reports, get_report
from src.pipeline import run_pipeline

log = get_logger("web")

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "templates")
_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "static")

app = Flask(__name__, template_folder=_TEMPLATE_DIR, static_folder=_STATIC_DIR)
# Кириллица в JSON-ответах без \u-эскейпов
app.json.ensure_ascii = False

# Состояние фонового анализа (защищено блокировкой — дашборд и бот в потоках)
_job_lock = threading.Lock()
_job = {"running": False, "last_error": None, "last_result": None, "started_at": None}


@app.route("/")
def index():
    return render_template("index.html", app_name="AI Trend Tracker", provider=settings.provider_name)


@app.route("/api/state")
def api_state():
    with _job_lock:
        job_snapshot = dict(_job)
    return jsonify({**get_stats(), "job": job_snapshot})


@app.route("/api/reports")
def api_reports():
    return jsonify([dict(r) for r in get_reports(20)])


@app.route("/api/report/<int:rid>")
def api_report(rid: int):
    r = get_report(rid)
    if r is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(r))


@app.route("/api/health")
def api_health():
    return jsonify({"ok": True, "provider": settings.provider_name, "app": "ai-trend-tracker"})


@app.route("/api/categories")
def api_categories():
    """Распределение трендов по категориям за последние 50 отчётов."""
    counts: dict[str, int] = {}
    for r in get_reports(50):
        try:
            data = json.loads(r["data"])
        except (json.JSONDecodeError, TypeError):
            continue
        for t in data.get("trends", []):
            cat = str(t.get("category", "Other")) or "Other"
            counts[cat] = counts.get(cat, 0) + 1
    return jsonify(counts)


@app.route("/analyze", methods=["POST"])
def analyze_now():
    """Запускает анализ в фоновом потоке."""
    with _job_lock:
        if _job["running"]:
            return jsonify({"ok": False, "error": "Анализ уже выполняется"}), 409
        _job["running"] = True
        _job["last_error"] = None
        _job["started_at"] = None

    def worker():
        try:
            _job["started_at"] = time.strftime("%H:%M:%S")
            _job["last_result"] = run_pipeline(notify=True, export=True).to_dict()
            log.info("Фоновый анализ завершён: %s", (_job["last_result"]["summary"] or "")[:60])
        except Exception as e:  # noqa: BLE001
            _job["last_error"] = str(e)
            log.exception("Фоновый анализ упал")
        finally:
            with _job_lock:
                _job["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


def main():
    setup_logging()
    init_db()
    log.info("Веб-дашборд: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
