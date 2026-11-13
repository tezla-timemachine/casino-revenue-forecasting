"""Index of every downloaded Board report: source, month, file, pages, size and checksum.

Reads the manifests written by the fetch scripts and writes docs/week4-report-index.csv
and docs/week4-report-index.md (a count per year and type, for a quick check).

    .venv/bin/python scripts/index_reports.py
"""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BOARD = RAW / "board-monthly"
DOCS = ROOT / "docs"
SOURCES = [
    ("ARR (market totals)", RAW, ["manifest.csv", "manifest_2015-01_2019-12.csv"],
     "Abbreviated Revenue Release, press release, 2 pages. Used for monthly_win.csv."),
    ("GRI (game-type detail)", BOARD, ["manifest.csv", "manifest_2015-01_2019-12.csv"],
     "Monthly Revenue Report (Gaming Revenue Information), about 48 pages. Used for game_types_monthly.csv."),
]


def pages(pdf: Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def main() -> None:
    rows = []
    for kind, folder, manifests, _ in SOURCES:
        for name in manifests:
            for r in csv.DictReader(open(folder / name)):
                pdf = folder / r["file"]
                rows.append({"report": kind, "month": r["report_month"], "file": r["file"],
                             "folder": str(pdf.parent.relative_to(ROOT)), "pages": pages(pdf) if pdf.exists() else "",
                             "bytes": pdf.stat().st_size if pdf.exists() else "", "source_url": r["url"],
                             "sha256": r.get("sha256", "")})
    rows.sort(key=lambda r: (r["report"], r["month"]))
    with (DOCS / "week4-report-index.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = ["# Index of downloaded Board reports", "",
             "Every report the project holds. Full file list: `docs/week4-report-index.csv`.", ""]
    for kind, _, _, note in SOURCES:
        mine = [r for r in rows if r["report"] == kind]
        months = sorted({r["month"] for r in mine})
        lines += [f"## {kind}", "", note, "",
                  f"- Reports: {len(mine)}, from {months[0]} to {months[-1]}",
                  f"- Total size: {sum(int(r['bytes']) for r in mine) / 1e6:.1f} MB",
                  f"- Pages per report: {min(int(r['pages']) for r in mine)} to {max(int(r['pages']) for r in mine)}", "",
                  "| Year | Reports | Months |", "|---|---|---|"]
        for year in sorted({m[:4] for m in months}):
            n = sum(1 for m in months if m.startswith(year))
            lines.append(f"| {year} | {n} | {'all 12' if n == 12 else n} |")
        lines.append("")
    lines += ["Not held: 2020 and 2021 (left out of training, D23).", ""]
    (DOCS / "week4-report-index.md").write_text("\n".join(lines))
    print(f"{len(rows)} reports indexed")


if __name__ == "__main__":
    main()
