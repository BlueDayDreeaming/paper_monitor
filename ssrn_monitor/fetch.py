from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlencode

from ssrn_monitor.dates import parse_approved_date_to_iso
from ssrn_monitor.http import JSON_ACCEPT, http_get
from ssrn_monitor.models import Paper, PaperAuthor
from ssrn_monitor.normalize import decode_and_clean_text, normalize_text


PAGE_SIZE = 50


def build_papers_page_url(api_url: str, page_index: int, page_size: int = PAGE_SIZE) -> str:
    separator = "&" if "?" in api_url else "?"
    query = urlencode({"index": page_index * page_size, "count": page_size, "sort": 0})
    return f"{api_url}{separator}{query}"


def transform_paper(raw_paper: dict[str, Any]) -> Paper:
    authors = [
        PaperAuthor(
            author_order=index + 1,
            ssrn_author_id=author.get("id"),
            author_name_raw=decode_and_clean_text(
                " ".join(part for part in [author.get("first_name"), author.get("last_name")] if part)
            ),
            author_name_clean=normalize_text(
                " ".join(part for part in [author.get("first_name"), author.get("last_name")] if part)
            ),
            author_url=author.get("url"),
        )
        for index, author in enumerate(raw_paper.get("authors", []))
    ]

    return Paper(
        abstract_id=int(raw_paper["id"]),
        approved_date_raw=raw_paper["approved_date"],
        approved_date_et=parse_approved_date_to_iso(raw_paper["approved_date"]),
        title_clean=decode_and_clean_text(raw_paper.get("title")),
        title_raw=raw_paper.get("title", "") or "",
        affiliations_clean=decode_and_clean_text(raw_paper.get("affiliations")),
        affiliations_raw=raw_paper.get("affiliations", "") or "",
        url=raw_paper.get("url") or f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={raw_paper['id']}",
        authors=authors,
    )


def fetch_papers_for_date(
    api_url: str,
    target_date_et: str,
    page_cap: int,
    proxies: Sequence[str] | None = None,
) -> tuple[list[Paper], dict[str, int], list[str]]:
    warnings: list[str] = []
    pages_scanned = 0
    papers_scanned = 0
    matched: list[Paper] = []

    for page_index in range(page_cap):
        page_url = build_papers_page_url(api_url, page_index)
        payload = json.loads(
            http_get(page_url, headers={"Accept": JSON_ACCEPT}, timeout=30, proxies=proxies).decode(
                "utf-8",
                errors="replace",
            )
        )

        raw_papers = payload.get("papers", [])
        papers = [transform_paper(paper) for paper in raw_papers]
        pages_scanned += 1
        papers_scanned += len(papers)

        matched.extend([paper for paper in papers if paper.approved_date_et == target_date_et])

        page_dates = sorted({paper.approved_date_et for paper in papers})
        oldest_date = page_dates[0] if page_dates else None
        newest_date = page_dates[-1] if page_dates else None

        if oldest_date and oldest_date < target_date_et:
            break

        if page_index + 1 == page_cap and newest_date and newest_date >= target_date_et:
            warnings.append(
                f"Reached page cap ({page_cap}) before seeing papers older than {target_date_et}. Increase --page-cap if needed."
            )

    stats = {
        "pages_scanned": pages_scanned,
        "papers_scanned": papers_scanned,
        "target_papers": len(matched),
    }
    return matched, stats, warnings
