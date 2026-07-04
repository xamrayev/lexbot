"""Tests for PDF export, gov-services lookup, and compliance findings parsing."""

from app.services.compliance.checker import parse_findings
from app.services.documents.pdf import build_pdf
from app.services.gov.catalog import GOV_SERVICES, find_services


def test_build_pdf_produces_valid_pdf():
    payload = build_pdf("# ПРИКАЗ № 1\n## Об отпуске\nПредоставить отпуск [ФИО] с [дата].")
    assert payload[:5] == b"%PDF-"
    assert len(payload) > 500


def test_gov_catalog_has_required_portals():
    urls = {s.url for s in GOV_SERVICES}
    assert "https://my.gov.uz" in urls
    assert "https://my.soliq.uz" in urls
    assert "https://lex.uz" in urls


def test_find_services_matches_business_registration():
    results = find_services("Как зарегистрировать ООО?")
    assert results and results[0].slug == "business-registration"


def test_find_services_matches_tax_in_uzbek():
    results = find_services("QQS hisobot topshirish muddati qachon?")
    assert any(s.slug == "tax-cabinet" for s in results)


def test_find_services_no_match_returns_empty():
    assert find_services("qwertyuiop asdfgh") == []


def test_parse_findings_normalizes_output():
    raw = """Вот результат:
    [
      {"severity": "CRITICAL", "issue": "Нет срока выплаты", "recommendation": "Добавить срок", "article": "ст. 155"},
      {"severity": "странное", "issue": "Мелкая неточность"},
      {"not_a_finding": true}
    ]"""
    findings = parse_findings(raw)
    assert len(findings) == 2
    assert findings[0]["severity"] == "critical"
    assert findings[1]["severity"] == "info"  # unknown severity normalized


def test_parse_findings_handles_garbage_and_empty():
    assert parse_findings("no json here") == []
    assert parse_findings("Документ корректен: []") == []
