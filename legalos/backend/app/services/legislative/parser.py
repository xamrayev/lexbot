"""Lex.uz / Norma.uz act parsing: HTML → clean text → per-article chunks.

Pure functions (no I/O) so they are unit-testable on fixture HTML:
- ``extract_act_text``  — strips markup/scripts/navigation and normalizes
  whitespace, so revision hashes react to *text* changes, not layout changes;
- ``split_by_articles`` — splits act text into article-level chunks
  (``N-modda`` for Uzbek, ``Статья N`` for Russian), falling back to plain
  window chunking when no article markers are found.
"""

import re

from app.services.documents.ingest import split_into_chunks

# Tags whose content is never part of the act's text.
_NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "iframe", "form", "button"]

# Article heading at line start: "115-modda." / "115-1-modda" (uz),
# "Статья 115." / "Статья 115-1" (ru).
_ARTICLE_PATTERNS = [
    re.compile(r"(?m)^(?P<num>\d+(?:-\d+)?)-modda\b", re.IGNORECASE),
    re.compile(r"(?m)^Статья\s+(?P<num>\d+(?:-\d+)?)\b", re.IGNORECASE),
]

# Articles longer than this are sub-chunked (keeping the article meta) so a
# single giant article doesn't blow up the LLM context.
MAX_ARTICLE_CHARS = 4000


def extract_act_text(html: str) -> str:
    """Extract normalized plain text from an act page.

    Layout markup, scripts and site chrome are dropped; every line is
    stripped and blank lines removed, so two pages with identical legal text
    but different markup normalize to the same string (stable content hash).
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def split_by_articles(text: str) -> list[dict]:
    """Split act text into ``{"article": str, "text": str}`` chunks.

    The preamble before the first article and texts without article markers
    get ``article == ""``. Requires at least two article headings to trust
    the pattern — a single accidental match falls back to window chunking.
    """
    matches: list[re.Match] = []
    for pattern in _ARTICLE_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) >= 2:
            break
    if len(matches) < 2:
        return [{"article": "", "text": chunk} for chunk in split_into_chunks(text)]

    chunks: list[dict] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        chunks.extend({"article": "", "text": part} for part in split_into_chunks(preamble))

    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        article_text = text[match.start() : end].strip()
        if not article_text:
            continue
        article = match.group("num")
        if len(article_text) > MAX_ARTICLE_CHARS:
            chunks.extend({"article": article, "text": part} for part in split_into_chunks(article_text))
        else:
            chunks.append({"article": article, "text": article_text})
    return chunks
