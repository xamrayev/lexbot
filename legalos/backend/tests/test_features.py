"""Tests for document generation, dataset parsing, and SSE formatting."""

import json

from app.api.v1.chat import _sse
from app.scripts.seed_labor_code import parse_dataset
from app.services.documents.generate import DOC_TYPES, build_docx, text_to_docx_paragraphs


def test_text_to_docx_paragraphs_styles():
    text = "# ПРИКАЗ № 15-к\n\n## О предоставлении отпуска\nПредоставить [ФИО] отпуск.\n\nОснование: ст. 141 ТК РУз."
    parsed = text_to_docx_paragraphs(text)
    assert parsed[0] == ("title", "ПРИКАЗ № 15-к")
    assert parsed[1] == ("heading", "О предоставлении отпуска")
    assert parsed[2][0] == "body"
    assert len(parsed) == 4  # blank lines dropped


def test_build_docx_produces_valid_docx():
    payload = build_docx("# Заголовок\nТекст документа.")
    assert payload[:2] == b"PK"  # DOCX is a ZIP container
    assert len(payload) > 1000


def test_doc_types_catalog():
    assert "order" in DOC_TYPES and "employment_contract" in DOC_TYPES


def test_parse_labor_code_dataset():
    raw = {
        "metadata": {"code_name": "MEHNAT KODEKSI"},
        "chunks": [
            {
                "id": "MK_RUz_115",
                "text": "115-modda. Ta'til 21 kundan kam bo'lmaydi.",
                "metadata": {"modda_number": "115", "modda_title": "Ta'til", "bob_title": "Mehnat ta'tili"},
            }
        ],
    }
    title, chunks = parse_dataset(raw)
    assert title == "MEHNAT KODEKSI"
    assert chunks[0]["meta"]["article"] == "115"
    assert chunks[0]["meta"]["url"].startswith("https://lex.uz")


def test_sse_frame_format():
    frame = _sse({"delta": "Салом"})
    assert frame.startswith("data: ") and frame.endswith("\n\n")
    assert json.loads(frame[len("data: ") : -2]) == {"delta": "Салом"}
