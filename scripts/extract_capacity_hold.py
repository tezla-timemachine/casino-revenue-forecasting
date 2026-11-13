"""Venue counts, table and machine counts, and hold, from the Board's Monthly Revenue Report.

For each area and month, from the area's 'All Nonrestricted Locations' detail page (found by its Total Gaming
figure, as in build_game_types.py), the current-month figures for:
  licensees            number of reporting licensees ('locations' in the 2015 to 2018 layout)
  table / slot units   number of tables and of slot machines (the section 'Total' lines)
  table / slot win     win, thousands of dollars
  table / slot hold    the report's 'win percent': win as a share of the amount bet (tables) or played (slots)
  baccarat units, win, hold, and twenty-one hold

These are source fields, printed in the report. Anything calculated from them (such as the amount bet)
is made later and labelled as derived.

Checks: table win + slot win (+ card games where the older layout leaves them out) = Total Gaming;
hold within a plausible range; every field present.

    .venv/bin/python scripts/extract_capacity_hold.py

Writes data/clean/capacity_hold_monthly.csv and data/clean/capacity_hold_checks.md.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_game_types as g  # page reading, number parsing, page finder, layout names

ROOT = g.ROOT
OUT = ROOT / "data" / "clean"
AREAS = ["Statewide", "LV Strip", "Downtown", "Laughlin", "Reno"]
FIELDS = ["licensees", "table_units", "table_win_k", "table_hold_pct", "slot_units", "slot_win_k", "slot_hold_pct",
          "baccarat_units", "baccarat_win_k", "baccarat_hold_pct", "twenty_one_hold_pct"]


def block(numbers: list[str]):
    """Current-month block of a full row: locations, units, win, % change, win percent."""
    if len(numbers) < 5:
        return None
    loc, units, win, chg, hold = (g.to_number(t) for t in numbers[:5])
    return {"units": int(units), "win": int(win), "hold": hold}


def read_new(page: str) -> dict:
    out, section, totals, cards = {}, "table", 0, 0
    m = re.search(r"Number of Reporting Licensees\s*-\s*(\d+)", page)
    out["licensees"] = int(m.group(1)) if m else None
    for line in page.splitlines():
        if not line.strip() or line.strip().startswith(("(", "*")):
            continue
        if "Slot Machines" in line:
            section = "slot"
            continue
        parts = re.split(r"\s{2,}", line.strip())
        label = parts[0]
        numbers = [t for t in " ".join(parts[1:]).split() if g.NUM.match(t)]
        if label.startswith("Total Gaming"):
            out["total_gaming_k"] = int(g.to_number(numbers[0])) if numbers else None
            break
        if label in g.SLOT_LINES:
            section = "slot"
        if label == "Total":
            totals += 1
            section = "slot" if totals == 2 else section
            b = block(numbers)
            if b:
                out[f"{section}_units"], out[f"{section}_win_k"], out[f"{section}_hold_pct"] = b["units"], b["win"], b["hold"]
        elif label == "Baccarat":
            b = block(numbers)
            if b:
                out["baccarat_units"], out["baccarat_win_k"], out["baccarat_hold_pct"] = b["units"], b["win"], b["hold"]
        elif label == "Twenty One":
            b = block(numbers)
            if b:
                out["twenty_one_hold_pct"] = b["hold"]
    out["cards_outside_table_total_k"] = cards
    return out


def read_old(page: str) -> dict:
    out, section = {}, "table"
    m = re.search(r"# OF REPORTING LOCATIONS\s*-+\s*(\d+)", page)
    out["licensees"] = int(m.group(1)) if m else None
    cards, cards_included = 0, True
    for line in page.splitlines():
        if not line.strip() or set(line.strip()) <= set("-=| "):
            continue
        if line.strip().startswith("("):
            break
        cells = [c.strip() for c in line.split("|")]
        label = cells[0].upper().rstrip(":")
        if not label:
            continue
        numbers = [t for t in (cells[1].split() if len(cells) > 1 else []) if g.NUM.match(t)]
        if label.startswith("TOTAL GAMING WIN"):
            out["total_gaming_k"] = int(g.to_number(numbers[0])) if numbers else None
            break
        if label == "SLOT MACHINES":
            section = "slot"
            continue
        if label.startswith("TOTAL GAMES") or label.startswith("TOTAL SLOT MACHINES"):
            target = "table" if label.startswith("TOTAL GAMES") else "slot"
            if target == "table":
                cards_included = "&" in label
            b = block(numbers)
            if b:
                out[f"{target}_units"], out[f"{target}_win_k"], out[f"{target}_hold_pct"] = b["units"], b["win"], b["hold"]
        elif label == "CARD GAMES" and len(numbers) >= 3:
            cards = int(g.to_number(numbers[2]))
        elif label == "BACCARAT":
            b = block(numbers)
            if b:
                out["baccarat_units"], out["baccarat_win_k"], out["baccarat_hold_pct"] = b["units"], b["win"], b["hold"]
        elif label == "TWENTY-ONE":
            b = block(numbers)
            if b:
                out["twenty_one_hold_pct"] = b["hold"]
    out["cards_outside_table_total_k"] = 0 if cards_included else cards
    return out


def main() -> None:
    manifest = {r["report_month"]: r["file"] for r in csv.DictReader(open(g.RAW / "manifest.csv"))}
    manifest.update({r["report_month"]: r["file"] for r in csv.DictReader(open(g.RAW / "manifest_2015-01_2019-12.csv"))})
    arr = list(csv.DictReader(open(g.ARR)))
    first = {(r["month"], r["area"]): int(r["first_published"]) for r in arr}
    latest = {(r["month"], r["area"]): int(r["gaming_win"]) for r in arr}
    rows, problems = [], []
    for month in sorted(manifest):
        pages = g.pages_text(g.RAW / manifest[month])
        for area in AREAS:
            page = g.find_page(pages, round(first[(month, area)] / 1000)) or g.find_page(pages, round(latest[(month, area)] / 1000))
            if page is None:
                problems.append(f"{month} {area}: detail page not found")
                continue
            data = read_old(page) if "TOTAL GAMING WIN" in page else read_new(page)
            row = {"month": month, "area": area, "source_file": manifest[month]}
            row.update({f: data.get(f) for f in FIELDS})
            missing = [f for f in FIELDS if row[f] is None]
            if missing:
                problems.append(f"{month} {area}: missing {', '.join(missing)}")
            total = data.get("total_gaming_k")
            if None not in (row["table_win_k"], row["slot_win_k"], total):
                gap = row["table_win_k"] + row["slot_win_k"] + data["cards_outside_table_total_k"] - total
                if abs(gap) > 2:
                    problems.append(f"{month} {area}: table + slots differ from Total Gaming by {gap:,}k")
            for f, low, high in [("table_hold_pct", 5, 30), ("slot_hold_pct", 3, 15), ("baccarat_hold_pct", -20, 45),
                                 ("twenty_one_hold_pct", 0, 30)]:
                v = row[f]
                if v is not None and not low <= v <= high:
                    problems.append(f"{month} {area}: {f} = {v} outside {low} to {high}")
            rows.append(row)

    with (OUT / "capacity_hold_monthly.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["month", "area"] + FIELDS + ["source_file"])
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Checks for data/clean/capacity_hold_monthly.csv", "",
             f"Months: {len(manifest)}. Areas: {', '.join(AREAS)}. Rows: {len(rows)}.",
             "Win in thousands of dollars; hold is the report's win percent.", ""]
    lines += [f"- {p}" for p in problems] or ["- Every row: all fields present, table + slots = Total Gaming, hold within range."]
    (OUT / "capacity_hold_checks.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:4]))
    print(f"problems: {len(problems)}")
    for p in problems[:40]:
        print(" ", p)


if __name__ == "__main__":
    main()
