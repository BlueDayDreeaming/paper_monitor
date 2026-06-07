from __future__ import annotations

from collections import defaultdict

from ssrn_monitor.models import MatchResult, Paper, WatchTarget
from ssrn_monitor.normalize import normalize_text, overlap_count, tokenize_for_overlap


def _build_unique_reason(author_name: str, overlap: int, duplicate_mode: bool) -> str:
    if not duplicate_mode and overlap > 0:
        return f'Unique normalized author name match for "{author_name}" with affiliation token overlap ({overlap}).'
    if not duplicate_mode:
        return f'Unique normalized author name match for "{author_name}" without affiliation token overlap.'
    if overlap > 0:
        return f'Duplicate normalized author name "{author_name}" resolved to rows with affiliation token overlap ({overlap}).'
    return f'Duplicate normalized author name "{author_name}" could not be resolved by affiliation overlap.'


def match_papers_to_targets(papers: list[Paper], targets: list[WatchTarget]) -> list[MatchResult]:
    name_index: dict[str, list[WatchTarget]] = defaultdict(list)
    for target in targets:
        name_index[target.normalized_name].append(target)

    matches: list[MatchResult] = []
    for paper in papers:
        paper_affiliation_tokens = tokenize_for_overlap(paper.affiliations_clean)
        for author in paper.authors:
            candidates = name_index.get(normalize_text(author.author_name_raw), [])
            if not candidates:
                continue

            scored = [
                (target, overlap_count(paper_affiliation_tokens, target.overlap_tokens))
                for target in candidates
            ]

            if len(scored) == 1:
                target, overlap = scored[0]
                matches.append(
                    MatchResult(
                        paper=paper,
                        target=target,
                        matched_author=author,
                        confidence="high" if overlap > 0 else "medium",
                        affiliation_overlap=overlap,
                        needs_review=False,
                        match_reason=_build_unique_reason(author.author_name_raw, overlap, False),
                    )
                )
                continue

            overlapping = [(target, overlap) for target, overlap in scored if overlap > 0]
            if overlapping:
                for target, overlap in overlapping:
                    matches.append(
                        MatchResult(
                            paper=paper,
                            target=target,
                            matched_author=author,
                            confidence="ambiguous",
                            affiliation_overlap=overlap,
                            needs_review=True,
                            match_reason=_build_unique_reason(author.author_name_raw, overlap, True),
                        )
                    )
                continue

            for target, overlap in scored:
                matches.append(
                    MatchResult(
                        paper=paper,
                        target=target,
                        matched_author=author,
                        confidence="ambiguous",
                        affiliation_overlap=overlap,
                        needs_review=True,
                        match_reason=_build_unique_reason(author.author_name_raw, overlap, True),
                    )
                )

    return matches
