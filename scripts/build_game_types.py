"""Game-type win (slots, table games, sports pool, race book, keno, ...) for statewide, the LV Strip and Reno.

Source: the Board's monthly revenue report (GRI), in data/raw/board-monthly/. Each area has a detail page with
the current month's win by game. The page is found by its 'Total Gaming' figure, which must equal the ARR win
for that area and month (decision D9 figure). Then three checks: table games + slots = Total Gaming, and the
game lines add up to their section totals.

    .venv/bin/python scripts/build_game_types.py

Writes data/clean/game_types_monthly.csv and data/clean/game_types_checks.md. Win is in dollars.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_reports as x  # ROOT, RAW (ARR folder); only used for paths here

ROOT = x.ROOT
RAW = ROOT / "data" / "raw" / "board-monthly"
ARR = ROOT / "data" / "clean" / "monthly_win.csv"
OUT = ROOT / "data" / "clean"
AREAS = {"Statewide": "Statewide", "LV Strip": "LV Strip", "Reno": "Reno"}
TOL_K = 2  # thousands of dollars: rounding allowed in the report's own sums
SLOT_LINES = {"1 Cent", "5 Cent", "25 Cent", "1 Dollar", "5 Dollars", "25 Dollars", "100 Dollars", "Multi Denomination"}
NUM = re.compile(r"^\(?-?[\d,]*\.?\d+\)?%?$")


def pages_text(pdf: Path) -> list[str]:
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    return [subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), str(pdf), "-"],
                           capture_output=True, text=True).stdout for p in range(1, n + 1)]


def to_number(token: str) -> float:
    neg = token.startswith("(")
    value = float(token.strip("()%").replace(",", ""))
    return -value if neg else value


TOTAL_RE = re.compile(r"Total Gaming(?: Win)?\s*\|?\s*(\(?-?[\d,]+\)?)", re.I)

# 2015 to 2019 reports use upper case names, | between columns, and their own names for some lines.
OLD_NAMES = {"TWENTY-ONE": "Twenty One", "CRAPS": "Craps", "ROULETTE": "Roulette", "ULTIM TEXAS HOLD'EM": "Ultim Texas Hold'em",
             "3-CARD POKER": "3-Card Poker", "BACCARAT": "Baccarat", "MINI-BACCARAT": "Mini-Baccarat", "KENO": "Keno",
             "BINGO": "Bingo", "LET IT RIDE": "Let It Ride", "PAI GOW": "Pai Gow", "PAI GOW POKER": "Pai Gow Poker",
             "RACE BOOK": "Race Book", "SPORTS POOL": "Sports Pool", "OTHER GAMES": "Other", "CARD GAMES": "Card Games",
             "1 CENT": "1 Cent", "5 CENT": "5 Cent", "25 CENT": "25 Cent", "1 DOLLAR": "1 Dollar", "5 DOLLAR": "5 Dollars",
             "25 DOLLAR": "25 Dollars", "100 DOLLAR": "100 Dollars", "MULTI DENOMINATION": "Multi Denomination",
             "MEGABUCKS": "Megabucks", "OTHER SLOT MACHINES": "Other"}


def total_gaming_k(page: str) -> int | None:
    m = TOTAL_RE.search(page)
    return int(to_number(m.group(1))) if m else None


def parse_old_page(page: str):
    """2015 to 2019 layout. Win is the third number of a row's current-month block (first number for totals)."""
    sections = {"table": {}, "slot": {}}
    section = "table"
    total_gaming = None
    blanks_old = []
    for line in page.splitlines():
        if not line.strip() or set(line.strip()) <= set("-=| "):
            continue
        if line.strip().startswith("("):  # sub-detail under Race Book or Sports Pool: stop before it
            break
        cells = [c.strip() for c in line.split("|")]
        label = cells[0].upper().rstrip(":")
        if not label:
            continue
        numbers = [t for t in (cells[1].split() if len(cells) > 1 else []) if NUM.match(t)]
        if label.startswith("TOTAL GAMING WIN"):
            total_gaming = int(to_number(numbers[0])) if numbers else None
            break
        if label == "SLOT MACHINES":
            section = "slot"
            continue
        if label.startswith("TOTAL GAMES") or label.startswith("TOTAL SLOT MACHINES"):
            target = "table" if label.startswith("TOTAL GAMES") else "slot"
            if numbers:
                sections[target]["__total__"] = int(to_number(numbers[2]))
                # From July 2015 the label is 'TOTAL GAMES & TABLES' and it already includes card games.
                sections[target]["__includes_cards__"] = "&" in label
            if target == "table":
                section = "table"
            continue
        if label in OLD_NAMES and OLD_NAMES[label] in SLOT_LINES or label in ("1 CENT", "5 CENT", "25 CENT", "1 DOLLAR", "5 DOLLAR", "25 DOLLAR", "100 DOLLAR", "MULTI DENOMINATION", "MEGABUCKS", "OTHER SLOT MACHINES"):
            section = "slot"
        if not numbers:
            continue
        name = re.sub(r"\s*\(\d\)$", "", OLD_NAMES.get(label, label.title())).strip()  # 'Race Book (1)' -> 'Race Book'
        is_other = label.startswith("OTHER")  # 'OTHER GAMES & TABLES', 'OTHER SLOT MACHINES': no location count
        if is_other:
            name = "Other"
        index = 1 if is_other else 2
        # A row with four numbers and no win amount: the 'win' slot holds a percentage change, and the win is blank.
        if not is_other and label != "CARD GAMES" and len(numbers) == 4 and abs(to_number(numbers[3])) < 1:
            sections[section][name] = 0
            blanks_old.append(name)
            continue
        if len(numbers) > index:
            sections[section][name] = int(to_number(numbers[index]))
    # In these reports 'TOTAL GAMES' leaves out card games, which sit below it. Add them, as the later layout does.
    if "__total__" in sections["table"] and "Card Games" in sections["table"] and not sections["table"].pop("__includes_cards__", False):
        sections["table"]["__total__"] += sections["table"]["Card Games"]
    sections["table"].pop("__includes_cards__", None)
    sections["slot"].pop("__includes_cards__", None)
    sections["blanks"] = blanks_old
    return sections, total_gaming


def find_page(pages: list[str], target_k: int) -> str | None:
    for page in pages:
        value = total_gaming_k(page)
        if value is not None and abs(value - target_k) <= 1:
            return page
    return None


def parse_page(page: str):
    if re.search(r"TOTAL GAMING WIN", page):
        return parse_old_page(page)
    return parse_new_page(page)


def parse_new_page(page: str):
    """Return ({'table': {...}, 'slot': {...}}, total gaming). Each block's 'Total' row is stored as '__total__'.

    A game's current-month win is the third number on its line. 'Other' rows have no location count, so
    their win is the second number. A line with ten or fewer numbers has no current-month figure (the report
    leaves it blank), so it is recorded as 0 and listed in the checks.
    """
    sections = {"table": {}, "slot": {}}
    section, totals_seen, blanks = "table", 0, []
    total_gaming = None
    for line in page.splitlines():
        if not line.strip():
            continue
        if "Slot Machines" in line:
            section = "slot"
            continue
        if line.strip().startswith(("(", "*")):
            continue
        parts = re.split(r"\s{2,}", line.strip())
        label = parts[0]
        numbers = [t for t in " ".join(parts[1:]).split() if NUM.match(t)]
        if label.startswith("Total Gaming"):
            total_gaming = int(to_number(numbers[0])) if numbers else None
            break
        if label == "Total":
            totals_seen += 1
            section = "slot" if totals_seen == 2 else section  # some reports have no 'Slot Machines' heading
            sections[section]["__total__"] = int(to_number(numbers[2]))
            continue
        if not numbers or "Number of Reporting" in label or " - " in label:
            continue
        name = re.sub(r"\s*\(\d\)$", "", label).strip()  # 'Race Book (1)' -> 'Race Book'
        if name in SLOT_LINES:
            section = "slot"  # some reports have no 'Slot Machines' heading, so the denomination lines mark the section
        index = 1 if name == "Other" else 2
        if len(numbers) <= 10 and name != "Other":
            blanks.append(name)
            sections[section][name] = 0
        elif len(numbers) > index:
            sections[section][name] = int(to_number(numbers[index]))
    sections["blanks"] = blanks
    return sections, total_gaming


def main() -> None:
    manifest = {r["report_month"]: r["file"] for r in csv.DictReader(open(RAW / "manifest.csv"))}
    manifest.update({r["report_month"]: r["file"] for r in csv.DictReader(open(RAW / "manifest_2015-01_2019-12.csv"))})
    arr = {(r["month"], r["area"]): int(r["first_published"]) for r in csv.DictReader(open(ARR))}
    arr_latest = {(r["month"], r["area"]): int(r["gaming_win"]) for r in csv.DictReader(open(ARR))}
    rows, problems = [], []
    for month in sorted(manifest):
        pages = pages_text(RAW / manifest[month])
        for label, area in AREAS.items():
            page = find_page(pages, round(arr[(month, area)] / 1000))
            if page is None:
                # Sep 2017: the Board's detail page matches the later revised ARR figure, not the first one.
                page = find_page(pages, round(arr_latest[(month, area)] / 1000))
                if page is None:
                    problems.append(f"{month} {label}: no page with Total Gaming matching ARR")
                    continue
                problems.append(f"{month} {label}: Board detail page matches the revised ARR figure, not the first-published one")
            sections, total = parse_page(page)
            blanks = sections.pop("blanks")
            table, slot = sections["table"], sections["slot"]
            table_total, slot_total = table.pop("__total__", None), slot.pop("__total__", None)
            if table_total is None or slot_total is None:
                problems.append(f"{month} {label}: section totals not found")
                continue
            if abs(sum(table.values()) - table_total) > TOL_K * 3:
                problems.append(f"{month} {label}: table lines sum to {sum(table.values()):,}, total {table_total:,}")
            if abs(sum(slot.values()) - slot_total) > TOL_K * 3:
                problems.append(f"{month} {label}: slot lines sum to {sum(slot.values()):,}, total {slot_total:,}")
            if total is None or abs(table_total + slot_total - total) > TOL_K:
                problems.append(f"{month} {label}: table {table_total:,} + slots {slot_total:,} != total {total}")
            for game in blanks:
                problems.append(f"{month} {label}: '{game}' blank for the month, recorded as 0")
            for section, lines in (("table", table), ("slot", slot)):
                for game, win in lines.items():
                    rows.append({"month": month, "area": label, "section": section, "game": game,
                                 "win_usd": win * 1000, "source_file": manifest[month]})
            rows.append({"month": month, "area": label, "section": "total", "game": "Table games total",
                         "win_usd": table_total * 1000, "source_file": manifest[month]})
            rows.append({"month": month, "area": label, "section": "total", "game": "Slot machines total",
                         "win_usd": slot_total * 1000, "source_file": manifest[month]})
            rows.append({"month": month, "area": label, "section": "total", "game": "Total gaming",
                         "win_usd": total * 1000, "source_file": manifest[month]})

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "game_types_monthly.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Checks for data/clean/game_types_monthly.csv", "",
             f"Months: {len(manifest)}. Areas: {', '.join(AREAS)}. Rows: {len(rows)}.", ""]
    lines += [f"- {p}" for p in problems] or ["- Every area and month: table + slots = Total Gaming, and the game lines add up to their section totals."]
    (OUT / "game_types_checks.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"Written: {(OUT / 'game_types_monthly.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
