from __future__ import annotations

import unittest

from ssrn_monitor.models import MatchResult, Paper, PaperAuthor, WatchTarget
from ssrn_monitor.normalize import tokenize_for_overlap
from ssrn_monitor.report import build_markdown_report


class ReportTest(unittest.TestCase):
    def test_report_includes_sections(self) -> None:
        target = WatchTarget(
            source_row_number=1,
            rank=1,
            school="University of Georgia",
            name="John Doe",
            school_unit="J.M. Tull School of Accounting",
            normalized_name="john doe",
            overlap_tokens=tokenize_for_overlap("University of Georgia", "J.M. Tull School of Accounting"),
        )
        paper = Paper(
            abstract_id=1,
            approved_date_raw="05 Jun 2026",
            approved_date_et="2026-06-05",
            title_clean="Sample Paper",
            title_raw="Sample Paper",
            affiliations_clean="University of Georgia - J.M. Tull School of Accounting",
            affiliations_raw="University of Georgia - J.M. Tull School of Accounting",
            url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1",
            authors=[PaperAuthor(1, 1, "John Doe", "john doe", None)],
        )
        match = MatchResult(
            paper=paper,
            target=target,
            matched_author=paper.authors[0],
            confidence="high",
            affiliation_overlap=3,
            needs_review=False,
            match_reason="ok",
        )
        content = build_markdown_report(
            "2026-06-05",
            {"pages_scanned": 1, "papers_scanned": 50, "target_papers": 10},
            [],
            [match],
        )
        self.assertIn("# SSRN ARN Monitor Report", content)
        self.assertIn("## High/Medium Confidence Matches", content)
        self.assertIn("Sample Paper", content)
        self.assertIn("- Unmatched papers: 9", content)


if __name__ == "__main__":
    unittest.main()
