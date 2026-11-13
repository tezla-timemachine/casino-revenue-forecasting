"""Calendar features for each month, calculated from the calendar alone (no download).

Every column starts with 'derived_' because none of them comes from a report.
Writes data/features/calendar.csv. Standard library only.

    python3 scripts/build_calendar.py
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "features" / "calendar.csv"
FIRST, LAST = (2015, 1), (2026, 12)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """The nth given weekday of a month (weekday: Monday=0)."""
    first = dt.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + dt.timedelta(days=offset + 7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int) -> dt.date:
    last = dt.date(year, month, calendar.monthrange(year, month)[1])
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)


def us_federal_holidays(year: int) -> list[dt.date]:
    """Common US federal holidays, the same set in every year (Nevada state holidays differ slightly)."""
    return [
        dt.date(year, 1, 1), nth_weekday(year, 1, 0, 3), nth_weekday(year, 2, 0, 3),
        last_weekday(year, 5, 0), dt.date(year, 6, 19), dt.date(year, 7, 4),
        nth_weekday(year, 9, 0, 1), nth_weekday(year, 10, 0, 2), dt.date(year, 11, 11),
        nth_weekday(year, 11, 3, 4), dt.date(year, 12, 25),
    ]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    y, m = FIRST
    while (y, m) <= LAST:
        days = calendar.monthrange(y, m)[1]
        dates = [dt.date(y, m, d) for d in range(1, days + 1)]
        holidays = [h for h in us_federal_holidays(y) if h.month == m]
        rows.append({
            "month": f"{y}-{m:02d}",
            "derived_days_in_month": days,
            "derived_weekend_days": sum(1 for d in dates if d.weekday() >= 5),
            "derived_friday_saturday_nights": sum(1 for d in dates if d.weekday() in (4, 5)),
            "derived_federal_holidays": len(holidays),
        })
        m += 1
        if m == 13:
            y, m = y + 1, 1
    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} months written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
