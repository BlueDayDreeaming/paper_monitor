from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


MONTH_MAP = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def shift_iso_date(iso_date: str, days: int) -> str:
    anchor = datetime.fromisoformat(f"{iso_date}T00:00:00+00:00")
    shifted = anchor + timedelta(days=days)
    return shifted.date().isoformat()


def default_target_date_et(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    current_et = current.astimezone(ZoneInfo("America/New_York"))
    return (current_et.date() - timedelta(days=1)).isoformat()


def parse_approved_date_to_iso(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Missing approved_date value from SSRN payload.")

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw

    parts = raw.split()
    if len(parts) == 3:
        day, month_text, year = parts
        month = MONTH_MAP.get(month_text[:3].lower())
        if not month:
            raise ValueError(f"Unsupported month in approved_date: {value}")
        return f"{year}-{month}-{day.zfill(2)}"

    normalized = raw.replace(",", "")
    parts = normalized.split()
    if len(parts) >= 3:
        month_text, day, year = parts[0], parts[1], parts[2]
        month = MONTH_MAP.get(month_text[:3].lower())
        if not month:
            raise ValueError(f"Unsupported month in approved_date: {value}")
        return f"{year}-{month}-{day.zfill(2)}"

    raise ValueError(f"Unrecognized approved_date format: {value}")
