"""Tests for Lex.uz act parsing: HTML extraction and article splitting."""

from pathlib import Path

from app.services.legislative.monitor import content_hash
from app.services.legislative.parser import extract_act_text, split_by_articles

FIXTURE = (Path(__file__).parent / "fixtures" / "lex_sample.html").read_text(encoding="utf-8")


def test_extract_drops_markup_scripts_and_chrome():
    text = extract_act_text(FIXTURE)
    assert "115-modda" in text
    assert "yigirma bir kalendar kundan" in text
    # site chrome, scripts and styles must not leak into the act text
    assert "analytics" not in text
    assert "Bosh sahifa" not in text  # nav
    assert "Chop etish" not in text  # button in footer
    assert "font: 14px" not in text  # style
    assert "<" not in text and ">" not in text


def test_markup_change_keeps_hash_stable():
    """Same legal text in different layout must produce the same content hash."""
    reskinned = FIXTURE.replace('<div class="doc">', '<main id="content" data-v2="true">').replace(
        "</div>", "</main>"
    ).replace("<p>", '<p class="para">').replace("<b>", "<strong>").replace("</b>", "</strong>")
    assert content_hash(extract_act_text(FIXTURE)) == content_hash(extract_act_text(reskinned))


def test_text_change_changes_hash():
    amended = FIXTURE.replace("yigirma bir", "yigirma besh")
    assert content_hash(extract_act_text(FIXTURE)) != content_hash(extract_act_text(amended))


def test_split_by_articles_uzbek():
    chunks = split_by_articles(extract_act_text(FIXTURE))
    by_article = {c["article"]: c["text"] for c in chunks if c["article"]}
    assert set(by_article) == {"114", "115"}
    assert "Yillik mehnat ta'tillari turlari" in by_article["114"]
    assert "yigirma bir kalendar kundan" in by_article["115"]
    # preamble (title) is kept with empty article marker
    assert any(c["article"] == "" and "MEHNAT KODEKSI" in c["text"] for c in chunks)


def test_split_by_articles_russian():
    text = (
        "ТРУДОВОЙ КОДЕКС\n"
        "Статья 141. Ежегодный основной отпуск\n"
        "Отпуск предоставляется продолжительностью не менее 21 календарного дня.\n"
        "Статья 142. Дополнительный отпуск\n"
        "Предоставляется отдельным категориям работников."
    )
    chunks = split_by_articles(text)
    articles = {c["article"] for c in chunks if c["article"]}
    assert articles == {"141", "142"}


def test_split_falls_back_without_article_markers():
    text = "Обычный текст постановления без статейной структуры. " * 50
    chunks = split_by_articles(text)
    assert chunks and all(c["article"] == "" for c in chunks)


def test_long_article_is_subchunked_with_meta():
    text = "1-modda. Kirish\nqisqa matn.\n2-modda. Uzun modda\n" + ("juda uzun matn. " * 400)
    chunks = split_by_articles(text)
    second = [c for c in chunks if c["article"] == "2"]
    assert len(second) > 1  # sub-chunked
    assert all(len(c["text"]) <= 4000 for c in second)
