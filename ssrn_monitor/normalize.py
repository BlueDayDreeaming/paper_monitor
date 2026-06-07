from __future__ import annotations

import html
import re
import unicodedata


OVERLAP_STOP_WORDS = {
    "and",
    "at",
    "business",
    "campus",
    "center",
    "centre",
    "college",
    "department",
    "economics",
    "faculty",
    "for",
    "graduate",
    "in",
    "institute",
    "international",
    "management",
    "of",
    "program",
    "programme",
    "research",
    "school",
    "studies",
    "the",
    "unit",
    "university",
}


def decode_and_clean_text(value: str | None) -> str:
    decoded = html.unescape(str(value or ""))
    decoded = re.sub(r"<[^>]*>", " ", decoded)
    decoded = decoded.replace("\u00a0", " ")
    decoded = re.sub(r"\s+", " ", decoded)
    return decoded.strip()


def normalize_text(value: str | None) -> str:
    cleaned = decode_and_clean_text(value)
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(char for char in cleaned if not unicodedata.combining(char))
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", cleaned)
    cleaned = cleaned.lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def tokenize_for_overlap(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        if not normalized:
            continue
        for token in normalized.split():
            if len(token) < 3:
                continue
            if token in OVERLAP_STOP_WORDS:
                continue
            tokens.add(token)
    return tokens


def overlap_count(left: set[str], right: set[str]) -> int:
    return sum(1 for token in left if token in right)
