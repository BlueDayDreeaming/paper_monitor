from __future__ import annotations

import unittest

from ssrn_monitor.match import match_papers_to_targets
from ssrn_monitor.models import Paper, PaperAuthor, WatchTarget
from ssrn_monitor.normalize import tokenize_for_overlap


class MatchTest(unittest.TestCase):
    def make_target(self, row: int, rank: int, name: str, school: str, school_unit: str = "") -> WatchTarget:
        return WatchTarget(
            source_row_number=row,
            rank=rank,
            school=school,
            name=name,
            school_unit=school_unit,
            normalized_name=name.lower(),
            overlap_tokens=tokenize_for_overlap(school, school_unit),
        )

    def make_paper(self, name: str, affiliations: str) -> Paper:
        return Paper(
            abstract_id=1,
            approved_date_raw="05 Jun 2026",
            approved_date_et="2026-06-05",
            title_clean="Sample",
            title_raw="Sample",
            affiliations_clean=affiliations,
            affiliations_raw=affiliations,
            url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1",
            authors=[
                PaperAuthor(
                    author_order=1,
                    ssrn_author_id=1,
                    author_name_raw=name,
                    author_name_clean=name.lower(),
                    author_url=None,
                )
            ],
        )

    def test_unique_match_with_overlap_is_high(self) -> None:
        targets = [
            self.make_target(1, 1, "John Doe", "University of Georgia", "J.M. Tull School of Accounting")
        ]
        paper = self.make_paper("John Doe", "University of Georgia - J.M. Tull School of Accounting")
        matches = match_papers_to_targets([paper], targets)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].confidence, "high")
        self.assertFalse(matches[0].needs_review)

    def test_duplicate_match_is_ambiguous(self) -> None:
        targets = [
            self.make_target(1, 1, "Jane Smith", "University of Florida"),
            self.make_target(2, 2, "Jane Smith", "University of Auckland"),
        ]
        paper = self.make_paper("Jane Smith", "Independent Researcher")
        matches = match_papers_to_targets([paper], targets)
        self.assertEqual(len(matches), 2)
        self.assertTrue(all(match.needs_review for match in matches))
        self.assertTrue(all(match.confidence == "ambiguous" for match in matches))


if __name__ == "__main__":
    unittest.main()
