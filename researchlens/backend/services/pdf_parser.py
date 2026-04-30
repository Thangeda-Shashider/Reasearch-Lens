"""
PDF parsing service.
Primary: PDFMiner.six  |  Fallback: PyMuPDF (for scanned/complex PDFs)
Extracts: title, abstract, authors, year, sections, references, full_text
"""
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SECTION_HEADERS: dict[str, list[str]] = {
    "abstract": ["abstract"],
    "introduction": ["1. introduction", "1 introduction", "introduction"],
    "related_work": [
        "2. related work", "related work", "related works",
        "literature review", "background and related work", "background",
    ],
    "methodology": [
        "methodology", "methods", "method", "proposed method",
        "approach", "system overview", "model",
    ],
    "results": [
        "results", "experiments", "evaluation",
        "experimental results", "findings", "experiments and results",
    ],
    "discussion": ["discussion", "analysis", "implications"],
    "conclusion": [
        "conclusion", "conclusions", "concluding remarks",
        "summary and conclusion", "summary",
    ],
    "references": ["references", "bibliography", "works cited"],
}

MATH_RE = [
    re.compile(r"\$[^\$]+\$"),
    re.compile(r"\\\[[^\]]+\\\]"),
    re.compile(r"\\[a-zA-Z]+\{[^}]*\}"),
]
FIGURE_RE = [
    re.compile(r"(?i)fig(?:ure)?\.?\s*\d+[^.]*\."),
    re.compile(r"(?i)table\s*\d+[^.]*\."),
]


# ─── Helpers ────────────────────────────────────────────────────────────────

def _clean_raw(text: str) -> str:
    text = re.sub(r"\x00", "", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _extract_year(text: str) -> Optional[int]:
    matches = re.findall(r"\b(19[89]\d|20[0-2]\d)\b", text[:3000])
    if not matches:
        return None
    from collections import Counter
    return int(Counter(matches).most_common(1)[0][0])


def _extract_authors(text: str) -> list[str]:
    header = text[:2000]
    patterns = [
        r"(?:Authors?|By)[:\s]+(.+?)(?:\n\n|\Z)",
        r"^([A-Z][a-z]+(?: [A-Z][a-z]+)+(?:,\s*[A-Z][a-z]+(?: [A-Z][a-z]+)+)*)\n",
    ]
    for pat in patterns:
        m = re.search(pat, header, re.MULTILINE)
        if m:
            raw = m.group(1)
            authors = re.split(r",\s*|\s+and\s+", raw)
            authors = [a.strip() for a in authors if 3 < len(a.strip()) < 60]
            if authors:
                return authors[:10]
    return []


def _extract_title(text: str, filename: str) -> str:
    lines = [l.strip() for l in text[:3000].split("\n") if l.strip()]
    for line in lines[:15]:
        if 10 < len(line) < 200 and not any(
            line.lower().startswith(h) for h in ("abstract", "author", "doi", "http")
        ):
            return line
    return Path(filename).stem


def _identify_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    lines = text.split("\n")
    current = "preamble"
    buf: list[str] = []

    for line in lines:
        stripped = line.strip().lower().rstrip(".")
        matched = None
        for sec_key, headers in SECTION_HEADERS.items():
            if any(stripped == h or stripped.startswith(h + " ") for h in headers):
                matched = sec_key
                break
        if matched:
            if buf:
                sections[current] = "\n".join(buf).strip()
            current = matched
            buf = []
        else:
            buf.append(line)
    if buf:
        sections[current] = "\n".join(buf).strip()
    return sections


def _extract_references(text: str) -> list[str]:
    ref_match = re.search(
        r"\n(?:references|bibliography|works cited)\s*\n", text, re.IGNORECASE
    )
    if not ref_match:
        return []
    ref_section = text[ref_match.end():]
    numbered = re.findall(r"\[\d+\].+?(?=\[\d+\]|\Z)", ref_section, re.DOTALL)
    if numbered:
        return [r.strip() for r in numbered[:100]]
    lines = [l.strip() for l in ref_section.split("\n") if len(l.strip()) > 25]
    return lines[:100]


# ─── Parsers ────────────────────────────────────────────────────────────────

def _parse_pdfminer(path: str) -> Optional[str]:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(path)
        return text if text and len(text) > 100 else None
    except Exception as e:
        logger.warning("PDFMiner failed for %s: %s", path, e)
        return None


def _parse_pymupdf(path: str) -> Optional[str]:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        pages = [page.get_text() for page in doc]
        doc.close()
        text = "\n".join(pages)
        return text if text and len(text) > 100 else None
    except Exception as e:
        logger.warning("PyMuPDF failed for %s: %s", path, e)
        return None


# ─── Public API ─────────────────────────────────────────────────────────────

def parse_pdf(pdf_path: str) -> dict:
    """
    Parse a PDF file and return structured metadata.

    Returns:
        {title, abstract, authors, year, sections, references, full_text}
    """
    logger.info("Parsing: %s", pdf_path)

    text = _parse_pdfminer(pdf_path)
    if not text:
        logger.info("Falling back to PyMuPDF: %s", pdf_path)
        text = _parse_pymupdf(pdf_path)

    filename = Path(pdf_path).name

    if not text:
        logger.error("Could not extract text from: %s", pdf_path)
        return {
            "title": Path(pdf_path).stem,
            "abstract": "",
            "authors": [],
            "year": None,
            "sections": {},
            "references": [],
            "full_text": "",
        }

    text = _clean_raw(text)
    sections = _identify_sections(text)

    preamble = sections.pop("preamble", "") or text[:3000]
    title = _extract_title(preamble, filename)
    abstract = sections.get("abstract", "")
    if not abstract:
        # Fallback: 500 chars after the title in preamble
        idx = preamble.find(title)
        abstract = preamble[idx + len(title): idx + len(title) + 800].strip()

    return {
        "title": title[:500],
        "abstract": abstract[:3000],
        "authors": _extract_authors(preamble),
        "year": _extract_year(text),
        "sections": {k: v[:15000] for k, v in sections.items()},
        "references": _extract_references(text),
        "full_text": text[:60000],
    }
