"""PDF rendering for generated documents (fpdf2).

Cyrillic/Uzbek text requires a Unicode TTF font: we look for DejaVu Sans in
standard system locations (installed in the backend image via
fonts-dejavu-core). Without it we fall back to Helvetica with lossy
latin-1 transliteration — good enough for smoke environments, wrong for prod.
"""

import os

from app.services.documents.generate import text_to_docx_paragraphs

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/DejaVuSans.ttf",
]
_FONT_BOLD_CANDIDATES = [p.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf") for p in _FONT_CANDIDATES]


def _find_font(candidates: list[str]) -> str | None:
    return next((p for p in candidates if os.path.exists(p)), None)


def build_pdf(text: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    regular = _find_font(_FONT_CANDIDATES)
    bold = _find_font(_FONT_BOLD_CANDIDATES)
    if regular:
        pdf.add_font("Doc", "", regular)
        pdf.add_font("Doc", "B", bold or regular)
        family = "Doc"
    else:
        family = "Helvetica"

    def _write(content: str, size: int, style: str, align: str = "L") -> None:
        if family == "Helvetica":  # core fonts are latin-1 only
            content = content.encode("latin-1", errors="replace").decode("latin-1")
        pdf.set_font(family, style, size)
        pdf.multi_cell(0, size * 0.6, content, align=align)

    for style, content in text_to_docx_paragraphs(text):
        if style == "title":
            _write(content, 16, "B", align="C")
            pdf.ln(4)
        elif style == "heading":
            _write(content, 13, "B")
            pdf.ln(2)
        else:
            _write(content, 11, "")
            pdf.ln(1)

    return bytes(pdf.output())
