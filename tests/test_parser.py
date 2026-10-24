"""Тесты модуля парсинга."""

from src.parser import clean_html, Article, articles_to_text, fetch_all_sources
# --- константы вынесены FORGE refactor ---
CONST_3 = 3



def test_clean_html_removes_tags():
    assert clean_html("<p>Привет <b>мир</b></p>") == "Привет мир"


def test_clean_html_removes_scripts():
    raw = "<p>Текст</p><script>alert(1)</script><style>x{}</style>"
    assert clean_html(raw) == "Текст alert(1) x{}"


def test_clean_html_unescapes_entities():
    assert clean_html("Tom &amp; Jerry") == "Tom & Jerry"


def test_articles_to_text_contains_fields():
    arts = [Article(title="Заголовок", link="https://x.ru/1", summary="Кратко", published="2026-01-01")]
    text = articles_to_text(arts)
    assert "Заголовок" in text
    assert "https://x.ru/1" in text
    assert "Статья 1" in text


def test_articles_to_text_truncates_summary():
    art = Article(title="T", link="L", summary="x" * 5000, published="")
    text = articles_to_text([art])
    assert text.count("x") <= 1000  # summary обрезан до 800 символов


def test_fetch_all_sources_dedups_by_link(monkeypatch):
    seen = []

    def fake_fetch(url, max_count):
        seen.append(url)
        if url == "https://a.ru/rss":
            return [
                Article(title="A1", link="https://x.ru/1", summary="", published=""),
                Article(title="A2", link="https://x.ru/2", summary="", published=""),
            ]
        return [
            Article(title="Дубль", link="https://x.ru/1", summary="", published=""),
            Article(title="B1", link="https://x.ru/3", summary="", published=""),
        ]

    monkeypatch.setattr("src.parser.fetch_articles", fake_fetch)
    result = fetch_all_sources(["https://a.ru/rss", "https://b.ru/rss"], 5)
    assert len(result) == CONST_3
    assert len({a.link for a in result}) == CONST_3
    assert seen == ["https://a.ru/rss", "https://b.ru/rss"]
