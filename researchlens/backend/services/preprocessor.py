"""
Text preprocessing pipeline.
Sentence tokenization (spaCy), stop word removal (NLTK + scientific corpus),
math/figure stripping, per-section clean sentence lists.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SCIENTIFIC_STOP_WORDS = {
    "fig", "figure", "table", "et", "al", "eq", "equation", "thus", "hence",
    "therefore", "however", "moreover", "furthermore", "shown", "shows", "cf",
    "section", "paper", "study", "work", "propose", "proposed", "using", "used",
    "also", "based", "given", "note", "approach", "result", "experiment", "data",
}

_MATH_PATTERNS = [
    re.compile(r"\$[^\$]+\$"),
    re.compile(r"\\\[[^\]]+\\\]"),
    re.compile(r"\\[a-zA-Z]+\{[^}]*\}"),
    re.compile(r"\b[A-Z][a-z]?\d+\b"),
]
_FIGURE_PATTERNS = [
    re.compile(r"(?i)fig(?:ure)?\.?\s*\d+[^.]*\."),
    re.compile(r"(?i)table\s*\d+[^.]*\."),
    re.compile(r"(?i)(?:see|as shown in|depicted in)\s+(?:fig|table|equation)"),
]
_URL_RE = re.compile(r"https?://\S+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\w+")
_WS_RE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    for pat in _MATH_PATTERNS:
        text = pat.sub(" ", text)
    for pat in _FIGURE_PATTERNS:
        text = pat.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def _get_stop_words() -> set[str]:
    try:
        import nltk
        try:
            sw = set(nltk.corpus.stopwords.words("english"))
        except LookupError:
            nltk.download("stopwords", quiet=True)
            sw = set(nltk.corpus.stopwords.words("english"))
        sw.update(SCIENTIFIC_STOP_WORDS)
        return sw
    except Exception:
        return SCIENTIFIC_STOP_WORDS.copy()


_stop_words: Optional[set[str]] = None


def get_stop_words() -> set[str]:
    global _stop_words
    if _stop_words is None:
        _stop_words = _get_stop_words()
    return _stop_words


def tokenize_sentences(text: str) -> list[str]:
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found – using regex tokenizer")
            sents = re.split(r"(?<=[.!?])\s+", text)
            return [s.strip() for s in sents if len(s.strip()) > 20]
        nlp.max_length = 2_000_000
        doc = nlp(text[:120_000])
        return [s.text.strip() for s in doc.sents if len(s.text.strip()) > 20]
    except Exception as e:
        logger.warning("Sentence tokenization error: %s", e)
        sents = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sents if len(s.strip()) > 20]


def remove_stop_words(text: str) -> str:
    sw = get_stop_words()
    words = text.split()
    return " ".join(w for w in words if w.lower() not in sw and len(w) > 2)


def preprocess_paper(sections: dict[str, str]) -> dict[str, list[str]]:
    """
    Given a dict of {section_name: raw_text}, return {section_name: [clean_sentences]}.
    Skips references section since it doesn't contribute to semantic analysis.
    """
    result: dict[str, list[str]] = {}
    for section_name, text in sections.items():
        if not text or section_name == "references":
            continue
        cleaned = _clean_text(text)
        sentences = tokenize_sentences(cleaned)
        # Keep sentences with a minimum word count
        result[section_name] = [s for s in sentences if len(s.split()) >= 5]
    return result


def get_clean_abstract(abstract: str) -> str:
    """Return a single clean string suitable for embedding."""
    cleaned = _clean_text(abstract)
    return remove_stop_words(cleaned)
