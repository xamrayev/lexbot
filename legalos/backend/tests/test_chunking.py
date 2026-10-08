"""Tests for structure-aware chunking (plan part 3)."""

from app.services.documents.ingest import CHUNK_SIZE, split_into_chunks, structured_chunks


def test_covers_whole_text_and_respects_max_length():
    text = "a" * 5000  # no sentence boundaries at all — hard-wrap path
    chunks = split_into_chunks(text)
    assert sum(len(c) for c in chunks) >= len(text)
    assert all(len(c) <= CHUNK_SIZE for c in chunks)


def test_does_not_cut_sentences_in_the_middle():
    sentence = "Это законченное предложение о трудовом договоре номер {i}. "
    text = "".join(sentence.format(i=i) for i in range(120))
    for chunk in split_into_chunks(text):
        assert chunk.endswith("."), f"chunk ends mid-sentence: ...{chunk[-40:]!r}"


def test_markdown_heading_starts_new_chunk_with_section_meta():
    text = (
        "Вводный абзац документа.\n\n"
        "## Порядок предоставления отпуска\n"
        "Отпуск предоставляется по графику. Продолжительность не менее 21 дня.\n\n"
        "## Оплата труда\n"
        "Зарплата выплачивается два раза в месяц."
    )
    chunks = structured_chunks(text)
    sections = [c["section"] for c in chunks]
    assert "" in sections  # preamble has no section
    assert "Порядок предоставления отпуска" in sections
    assert "Оплата труда" in sections
    vacation = next(c for c in chunks if c["section"] == "Порядок предоставления отпуска")
    assert "по графику" in vacation["text"]
    # content of one section never leaks into another
    payment = next(c for c in chunks if c["section"] == "Оплата труда")
    assert "отпуск" not in payment["text"].lower()


def test_overlap_carries_trailing_sentences():
    sentence = "Пункт договора номер {i} регулирует отдельное условие сторон. "
    text = "".join(sentence.format(i=i) for i in range(80))
    chunks = split_into_chunks(text)
    assert len(chunks) > 1
    # the first sentence of chunk N+1 must repeat the tail of chunk N
    for prev, nxt in zip(chunks, chunks[1:]):
        first_sentence = nxt.splitlines()[0]
        assert first_sentence in prev


def test_empty_and_whitespace_only():
    assert split_into_chunks("") == []
    assert split_into_chunks("   \n\n   ") == []
