"""Build the clean monthly gaming-win table from the 57 reports, using the newest figure for each month (D9).

For each month, the figure comes from the report a year later, in its 'same month last year' column,
because that is the newest version the Board has published. The newest report has no later version,
so its own current-month figure is used. Each row also records the figure first published and whether it was revised.

    .venv/bin/python scripts/build_table.py

Writes data/clean/monthly_win.csv and data/clean/build_checks.md.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_reports as x  # the two readers and the row keys (same folder)

OUT = x.ROOT / "data" / "clean"
TOLERANCE = x.TOLERANCE


def read_report(pdf: Path) -> dict:
    """Method A first; method B and OCR only if A finds no table."""
    rows = dict(x.keyed(x.method_a(pdf)))
    if not rows:
        rows = dict(x.keyed(x.method_b(pdf)))
    if not rows:
        rows = dict(x.keyed(x.method_b_ocr(pdf)))
    return rows


def describe(key: str) -> tuple[str, str, str]:
    """Return (parent, area, level) for a row key, with clear names for the 'Balance of County' rows."""
    if key == "Statewide":
        return "", "Statewide", "statewide"
    if key in x.COUNTIES:
        return "Statewide", key, "county"
    if " | " in key:
        parent, area = key.split(" | ")
        if area == "Balance of County":
            area = f"Balance of {parent.replace(' County', '')}"
        return parent, area, "market"
    if key == "Other":
        return "Statewide", "Other", "other"
    return "Statewide", key, "market"


def main() -> None:
    # Two manifests: 2022 to 2026, and the 2015 to 2019 history. Months with no later report keep their own figure.
    manifest = list(csv.DictReader(open(x.RAW / "manifest.csv")))
    manifest += list(csv.DictReader(open(x.RAW / "manifest_2015-01_2019-12.csv")))
    reports = {m["report_month"]: (m["file"], read_report(x.RAW / m["file"])) for m in manifest}
    OUT.mkdir(parents=True, exist_ok=True)

    table = []
    for month in sorted(reports):
        own_file, own = reports[month]
        y, mo = map(int, month.split("-"))
        later_month = f"{y + 1}-{mo:02d}"
        later_file, later = reports.get(later_month, (None, None))
        for key, values in own.items():
            if later is not None and key in later:
                win, source_file, basis = later[key][1], later_file, f"{later_month} report, same month last year"
            else:
                win, source_file, basis = values[0], own_file, f"{month} report, current month"
            parent, area, level = describe(key)
            first = values[0]
            revised = later is not None and key in later and first != later[key][1]
            table.append({
                "month": month, "parent": parent, "area": area, "level": level, "gaming_win": win,
                "source_file": source_file, "source_basis": basis,
                "first_published": first, "revised": "yes" if revised else "no",
                "revision_pct": f"{(first - win) / win:+.4%}" if revised else "",
            })

    with (OUT / "monthly_win.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)

    # ---- checks -------------------------------------------------------------------------------
    by_month: dict[str, dict] = {}
    for r in table:
        by_month.setdefault(r["month"], {})[r["area"] if r["level"] != "market" or r["parent"] == "Statewide"
                                           else f"{r['parent']} | {r['area']}"] = int(r["gaming_win"])
    checks = ["# Build checks for data/clean/monthly_win.csv", "",
              f"Months: {len(reports)} ({min(reports)} to {max(reports)}). Rows: {len(table)}.", ""]
    row_problems = [f"{m}: {len(v)} rows" for m, v in sorted(by_month.items()) if len(v) != x.EXPECTED_ROWS]
    checks.append(f"- Rows per month: {'all 20' if not row_problems else '; '.join(row_problems)}")

    sum_problems = []
    for month, v in sorted(by_month.items()):
        groups = [("Clark County", [f"Clark County | {a}" for a in sorted(x.CLARK | {'Balance of County'})]),
                  ("Washoe County", [f"Washoe County | {a}" for a in sorted(x.WASHOE | {'Balance of County'})]),
                  ("Elko County", [f"Elko County | {a}" for a in sorted(x.ELKO | {'Balance of County'})]),
                  ("Statewide", ["Clark County", "Washoe County", "South Lake Tahoe", "Elko County",
                                 "Carson Valley Area", "Other"])]
        for parent, children in groups:
            if parent in v and all(c in v for c in children):
                gap = v[parent] - sum(v[c] for c in children)
                if abs(gap) > TOLERANCE:
                    sum_problems.append(f"{month} {parent}: {gap:,}")
    checks.append(f"- Totals add up within ${TOLERANCE}: {'yes, every month' if not sum_problems else '; '.join(sum_problems)}")

    revised = [r for r in table if r["revised"] == "yes"]
    checks.append(f"- Rows using a later report's figure: {sum(1 for r in table if 'same month last year' in r['source_basis'])}")
    checks.append(f"- Rows where the newest report's own figure is used: {sum(1 for r in table if 'current month' in r['source_basis'])}")
    checks.append(f"- Rows revised since first publication: {len(revised)}")
    checks.append(f"- Revisions over 1%: {sum(1 for r in revised if abs(float(r['revision_pct'].rstrip('%'))) > 1)}")
    checks.append("")
    checks.append("Rows that use the newest report's own figure (the last 12 months, Oct 2025 to Sep 2026) are the only figures "
                  "not yet revised by the Board, so they may change in later reports.")
    (OUT / "build_checks.md").write_text("\n".join(checks) + "\n")

    print("\n".join(checks))
    print(f"\nWritten: {(OUT / 'monthly_win.csv').relative_to(x.ROOT)}")


if __name__ == "__main__":
    main()
