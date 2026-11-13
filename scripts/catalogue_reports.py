"""Group every downloaded Board report by its layout, so each distinct format appears once.

For each PDF, the script records features of its text (headings, separators, page count) and groups
reports that share them. Output: docs/week4-report-catalogue.csv (one row per report, with its format group).

    .venv/bin/python scripts/catalogue_reports.py
"""
from __future__ import annotations

import csv
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BOARD = RAW / "board-monthly"
DOCS = ROOT / "docs"


def text_of(pdf: Path, page: int) -> str:
    return subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
                          capture_output=True, text=True).stdout


def fingerprint(pdf: Path, kind: str) -> dict:
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    if kind == "ARR":
        first = text_of(pdf, 1)
        return {"pages": pages, "fee_page": "Fee Tax Collections" in first,
                "current_period_header": "Current Period" in first, "fiscal_ytd_header": "Fiscal Year-to" in first,
                "upper_case_titles": "NEVADA GAMING CONTROL BOARD" in first.upper() and "Win Revenue Summary" not in first}
    # GRI: check the first two pages for the layout markers
    text = text_of(pdf, 1) + text_of(pdf, 4)
    return {"pages": pages,
            "upper_case_titles": "GAMING REVENUE REPORT" in text,
            "bars_between_columns": " | " in text,
            "win_in_thousands": "Thousands" in text or "thousands" in text,
            "section_headings": "Table, Counter and Card Games" in text or "TABLE, COUNTER" in text.upper(),
            "slot_heading": "Slot Machines" in text or "SLOT MACHINES" in text,
            "three_month_block": "Three Months" in text or "THREE MONTH SUMMARY" in text.upper(),
            "total_label": "Total Gaming" if "Total Gaming" in text else ("TOTAL GAMING WIN" if "TOTAL GAMING WIN" in text.upper() else "none")}


def main() -> None:
    rows = []
    for kind, folder, manifests in [("ARR", RAW, ["manifest.csv", "manifest_2015-01_2019-12.csv"]),
                                    ("GRI", BOARD, ["manifest.csv", "manifest_2015-01_2019-12.csv"])]:
        for name in manifests:
            for r in csv.DictReader(open(folder / name)):
                pdf = folder / r["file"]
                fp = fingerprint(pdf, kind)
                rows.append({"kind": kind, "month": r["report_month"], "file": r["file"], **fp})
    # Each distinct combination of layout markers is one format group.
    keys = sorted({tuple(sorted((k, str(v)) for k, v in r.items() if k not in ("kind", "month", "file")))
                   for r in rows if True}, key=str)
    group_of = {k: i + 1 for i, k in enumerate(keys)}
    for r in rows:
        r["format_group"] = group_of[tuple(sorted((k, str(v)) for k, v in r.items()
                                                    if k not in ("kind", "month", "file", "format_group")))]
    rows.sort(key=lambda r: (r["kind"], r["month"]))
    fields = ["kind", "month", "file", "format_group"] + sorted({k for r in rows for k in r} - {"kind", "month", "file", "format_group"})
    with (DOCS / "week4-report-catalogue.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["kind"], r["format_group"])].append(r)
    for (kind, g), members in sorted(groups.items()):
        months = sorted(m["month"] for m in members)
        print(f"{kind} group {g}: {len(members)} reports, {months[0]} to {months[-1]}, e.g. {members[0]['file']}")


if __name__ == "__main__":
    main()
