"""Read every monthly Nevada ARR report two ways and cross-check the results.

Method A: pdftotext (Poppler) in layout mode, then rules.
Method B: pdfplumber (a different PDF text engine) with word positions, then the same rules.
          If a report has no text table on page 1 (the January 2025 picture page), Tesseract OCR
          reads the page image instead.

Checks: A against B for every number; each county adds up to its markets; the counties add up
to the statewide total; each month's figure matches the same month in the report a year later.

    .venv/bin/python scripts/extract_reports.py

Writes data/extracted/method_a.csv, method_b.csv and cross_check.md. Decisions: D9, D10.
"""
from __future__ import annotations

import csv
import re
import subprocess
import tempfile
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"
COLS = ["month", "prior_month", "pct_month", "fytd", "prior_fytd", "pct_fytd"]
MONEY_COLS = [0, 1, 3, 4]
EXPECTED_ROWS = 20          # statewide, 3 counties, 15 markets, South Lake Tahoe, Carson Valley, Other
TOLERANCE = 10              # dollars; the report rounds each figure, so parts can differ from totals by a few dollars
MINOR_REVISION = 0.001      # 0.1%: noted
REVISION_FLAG = 0.01        # 1%: flagged for a person to review

MONEY = re.compile(r"^-?\d[\d,]*$")
PCT = re.compile(r"^-?\d+\.\d+%$")
SHAPE = ["m", "m", "p", "m", "m", "p"]
CLARK = {"LV Strip", "Downtown", "North Las Vegas", "Laughlin", "Boulder Strip", "Mesquite"}
WASHOE = {"Reno", "Sparks", "North Lake Tahoe"}
ELKO = {"Wendover"}
COUNTIES = {"Clark County", "Washoe County", "Elko County"}


def split_row(tokens: list[str]):
    """Return (label, six values) if a line ends with six numbers in the report's pattern, else None."""
    tokens = [t for t in tokens if t != "|" and not re.fullmatch(r"\*+", t)]  # OCR bars, footnote stars: *, **
    if len(tokens) < 7:
        return None
    tail = tokens[-6:]
    kinds = ["p" if PCT.match(t) else "m" if MONEY.match(t) else "?" for t in tail]
    if kinds != SHAPE:
        return None
    label = " ".join(tokens[:-6])
    if not label:
        return None
    values = [float(t[:-1]) if t.endswith("%") else int(t.replace(",", "")) for t in tail]
    return label, values


def rows_from_lines(lines: list[str]):
    return [parsed for parsed in (split_row(line.split()) for line in lines) if parsed]


def method_a(pdf: Path):
    text = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "1", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout
    return rows_from_lines(text.splitlines())


def method_b(pdf: Path):
    with pdfplumber.open(pdf) as doc:
        words = doc.pages[0].extract_words()
    words.sort(key=lambda w: (w["top"], w["x0"]))
    lines, current, line_top = [], [], None
    for w in words:  # a new line starts when the vertical position moves by more than 3 points
        if line_top is None or w["top"] - line_top > 3:
            if current:
                lines.append(current)
            current, line_top = [], w["top"]
        current.append(w)
    if current:
        lines.append(current)
    return rows_from_lines([" ".join(w["text"] for w in sorted(line, key=lambda w: w["x0"])) for line in lines])


def method_b_ocr(pdf: Path):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "300", "-f", "1", "-l", "1", "-png", str(pdf), f"{tmp}/page"], check=True)
        image = next(Path(tmp).glob("page*.png"))
        text = subprocess.run(["tesseract", str(image), "-", "--psm", "6"],
                              capture_output=True, text=True, check=True).stdout
    # OCR sometimes splits a number in two ("123,427 623" -> "123,427,623"); rejoin those.
    text = re.sub(r"(\d,\d{3}) (\d{3})(?=\s|$)", r"\1,\2", text, flags=re.M)
    return rows_from_lines(text.splitlines())


def keyed(rows):
    """Give each row a unique key. 'Balance of County' is keyed by the county above it."""
    out, county = [], None
    for label, values in rows:
        if label in COUNTIES:
            county = label
            key = label
        elif label in CLARK:
            key = f"Clark County | {label}"
        elif label in WASHOE:
            key = f"Washoe County | {label}"
        elif label in ELKO:
            key = f"Elko County | {label}"
        elif label == "Balance of County":
            key = f"{county} | {label}"
        else:
            key = label
        out.append((key, values))
    return out


def arithmetic(rows: dict) -> list[str]:
    groups = [
        ("Clark County", [f"Clark County | {x}" for x in sorted(CLARK | {"Balance of County"})]),
        ("Washoe County", [f"Washoe County | {x}" for x in sorted(WASHOE | {"Balance of County"})]),
        ("Elko County", [f"Elko County | {x}" for x in sorted(ELKO | {"Balance of County"})]),
        ("Statewide", ["Clark County", "Washoe County", "South Lake Tahoe", "Elko County",
                       "Carson Valley Area", "Other"]),
    ]
    problems = []
    for parent, children in groups:
        missing = [k for k in [parent, *children] if k not in rows]
        if missing:
            problems.append(f"{parent}: rows missing: {', '.join(missing)}")
            continue
        for col in MONEY_COLS:
            gap = rows[parent][col] - sum(rows[c][col] for c in children)
            if abs(gap) > TOLERANCE:
                problems.append(f"{parent} {COLS[col]}: parts differ from total by {gap:,}")
    return problems


def main() -> None:
    manifest = list(csv.DictReader(open(RAW / "manifest.csv")))
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    for m in manifest:
        pdf = RAW / m["file"]
        a_list = keyed(method_a(pdf))
        b_list = keyed(method_b(pdf))
        b_source = "pdfplumber"
        if not b_list:
            b_list, b_source = keyed(method_b_ocr(pdf)), "OCR"
        files.append({"month": m["report_month"], "file": m["file"], "a_list": a_list,
                      "b_list": b_list, "b_source": b_source,
                      "a": dict(a_list), "b": dict(b_list)})
        print(f"{m['report_month']}  A rows {len(a_list):>2}  B rows {len(b_list):>2} ({b_source})  {m['file']}")

    for name, field in [("method_a.csv", "a_list"), ("method_b.csv", "b_list")]:
        with (OUT / name).open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["report_month", "file", "key", *COLS])
            for f in files:
                for key, values in f[field]:
                    w.writerow([f["month"], f["file"], key, *values])

    report = ["# Cross-check of the Nevada ARR reports", "",
              "Generated by `scripts/extract_reports.py`. Method A = pdftotext layout; method B = pdfplumber (OCR where the page is a picture).",
              "", "## 1. Row counts", "", "| Month | A rows | B rows | B source | Problems |", "|---|---|---|---|---|"]
    disagreements, arithmetic_problems = [], []
    for f in files:
        problems = []
        if len(f["a_list"]) != EXPECTED_ROWS or len(f["b_list"]) != EXPECTED_ROWS:
            problems.append(f"expected {EXPECTED_ROWS} rows")
        if len(f["a_list"]) != len(f["a"]):
            problems.append("duplicate keys in A")
        if not f["a_list"]:
            problems.append("A found no table (picture page)")
        report.append(f"| {f['month']} | {len(f['a_list'])} | {len(f['b_list'])} | {f['b_source']} | {'; '.join(problems) or '-'} |")
        if not f["a"]:
            continue  # no text table for method A; this month is checked against the later report instead
        for key in sorted(set(f["a"]) | set(f["b"])):
            if key not in f["a"] or key not in f["b"]:
                disagreements.append(f"{f['month']} {key}: only in one method")
            elif f["a"][key] != f["b"][key]:
                for i, (x, y) in enumerate(zip(f["a"][key], f["b"][key])):
                    if x != y:
                        disagreements.append(f"{f['month']} {key} {COLS[i]}: A={x} B={y}")
        for label, rows in [("A", f["a"]), ("B", f["b"])]:
            if rows:
                arithmetic_problems += [f"{f['month']} [{label}] {p}" for p in arithmetic(rows)]

    # Year-later check: a month's current figure against the same month in the report a year later.
    by_month = {f["month"]: f["a"] or f["b"] for f in files}
    revisions = []
    for month, rows in by_month.items():
        y, mth = map(int, month.split("-"))
        later = by_month.get(f"{y + 1}-{mth:02d}")
        if not later:
            continue
        for key, values in rows.items():
            if key in later:
                first, reported_later = values[0], later[key][1]
                pct = (first - reported_later) / reported_later if reported_later else 0.0
                revisions.append((month, key, first, reported_later, pct))
    flagged = [r for r in revisions if abs(r[4]) > REVISION_FLAG]
    minor = [r for r in revisions if MINOR_REVISION < abs(r[4]) <= REVISION_FLAG]
    pcts = [abs(r[4]) for r in revisions]

    report += ["", "## 2. Method A against method B", ""]
    report += [f"- {d}" for d in disagreements] or ["All numbers agree."]
    report += ["", "## 3. Totals", ""]
    report += [f"- {p}" for p in arithmetic_problems] or [f"Every county and the statewide total add up within ${TOLERANCE}."]
    report += ["", "## 4. Same month a year later", "",
               f"- Figures compared: {len(revisions)}",
               f"- Identical: {sum(1 for r in revisions if r[2] == r[3])}",
               f"- Largest difference: {max(pcts):.4%}" if pcts else "- No comparisons",
               f"- Between {MINOR_REVISION:.1%} and {REVISION_FLAG:.0%} (noted): {len(minor)}",
               f"- Over {REVISION_FLAG:.0%} (flagged for review): {len(flagged)}"]
    report += [f"  - {m} {k}: first {a:,}, later {b:,} ({p:+.2%})" for m, k, a, b, p in sorted(flagged, key=lambda r: -abs(r[4]))]
    (OUT / "cross_check.md").write_text("\n".join(report) + "\n")

    print(f"\nA vs B disagreements: {len(disagreements)}")
    print(f"Total problems: {len(arithmetic_problems)}")
    print(f"Year-later comparisons: {len(revisions)}, identical {sum(1 for r in revisions if r[2] == r[3])}, "
          f"over {REVISION_FLAG:.0%}: {len(flagged)}, largest {max(pcts):.4%}" if pcts else "No year-later comparisons")
    print(f"Written to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
