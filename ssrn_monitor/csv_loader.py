from __future__ import annotations

import csv
from pathlib import Path

from ssrn_monitor.models import WatchTarget
from ssrn_monitor.normalize import normalize_text, tokenize_for_overlap


def load_watch_targets(csv_path: str | Path) -> list[WatchTarget]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    targets: list[WatchTarget] = []
    for index, row in enumerate(rows, start=1):
        targets.append(
            WatchTarget(
                source_row_number=index,
                rank=int(row["rank"]),
                school=row.get("school", "") or "",
                name=row.get("name", "") or "",
                school_unit=row.get("school_unit", "") or "",
                normalized_name=normalize_text(row.get("name")),
                overlap_tokens=tokenize_for_overlap(row.get("school"), row.get("school_unit")),
            )
        )
    return targets
