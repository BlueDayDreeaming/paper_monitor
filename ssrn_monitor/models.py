from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WatchTarget:
    source_row_number: int
    rank: int
    school: str
    name: str
    school_unit: str
    normalized_name: str
    overlap_tokens: set[str]


@dataclass(slots=True)
class PaperAuthor:
    author_order: int
    ssrn_author_id: int | None
    author_name_raw: str
    author_name_clean: str
    author_url: str | None


@dataclass(slots=True)
class Paper:
    abstract_id: int
    approved_date_raw: str
    approved_date_et: str
    title_clean: str
    title_raw: str
    affiliations_clean: str
    affiliations_raw: str
    url: str
    authors: list[PaperAuthor]


@dataclass(slots=True)
class MatchResult:
    paper: Paper
    target: WatchTarget
    matched_author: PaperAuthor
    confidence: str
    affiliation_overlap: int
    needs_review: bool
    match_reason: str
