from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ssrn_monitor.models import MatchResult


def _group_matches(matches: list[MatchResult]) -> list[tuple[int, list[MatchResult]]]:
    grouped: dict[int, list[MatchResult]] = defaultdict(list)
    for match in matches:
        grouped[match.paper.abstract_id].append(match)
    return sorted(grouped.items(), key=lambda item: item[0])


def _render_group(group: list[MatchResult]) -> str:
    paper = group[0].paper
    lines = [
        f"### {paper.title_clean}",
        f"- SSRN: {paper.url}",
        f"- Approved date: {paper.approved_date_raw} ({paper.approved_date_et} ET)",
        f"- Authors: {'; '.join(author.author_name_raw for author in paper.authors)}",
        f"- Affiliation: {paper.affiliations_clean or '(blank)'}",
    ]
    for match in sorted(group, key=lambda item: item.target.source_row_number):
        lines.append(
            f"- row {match.target.source_row_number} | rank {match.target.rank} | "
            f"{match.target.name} | {match.target.school} | {match.confidence} | "
            f"overlap={match.affiliation_overlap}"
        )
    return "\n".join(lines)


def build_markdown_report(
    target_date_et: str,
    stats: dict[str, int],
    warnings: list[str],
    matches: list[MatchResult],
) -> str:
    grouped = _group_matches(matches)
    clean_groups = [group for _, group in grouped if all(not item.needs_review for item in group)]
    ambiguous_groups = [group for _, group in grouped if any(item.needs_review for item in group)]
    unmatched_papers = max(stats["target_papers"] - len(grouped), 0)

    lines = [
        "# SSRN ARN Monitor Report",
        "",
        f"- Target date (ET): {target_date_et}",
        f"- Pages scanned: {stats['pages_scanned']}",
        f"- Papers scanned: {stats['papers_scanned']}",
        f"- Papers on target date: {stats['target_papers']}",
        f"- Matched papers: {len(grouped)}",
        f"- Unmatched papers: {unmatched_papers}",
        f"- High/medium confidence papers: {len(clean_groups)}",
        f"- Ambiguous papers: {len(ambiguous_groups)}",
    ]

    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.extend(["", "## High/Medium Confidence Matches", ""])
    if not clean_groups:
        lines.append("- none")
    else:
        for group in clean_groups:
            lines.append(_render_group(group))
            lines.append("")

    lines.extend(["", "## Ambiguous Matches", ""])
    if not ambiguous_groups:
        lines.append("- none")
    else:
        for group in ambiguous_groups:
            lines.append(_render_group(group))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(report_dir: str | Path, target_date_et: str, content: str) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{target_date_et}.md"
    path.write_text(content, encoding="utf-8")
    return path
