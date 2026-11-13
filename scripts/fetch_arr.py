"""Find the Nevada Gaming Control Board monthly revenue reports and save them to data/raw/.

Uses only the Python standard library, so there is nothing to install.

    python3 scripts/fetch_arr.py               # list the reports and write data/raw/manifest.csv (no PDFs saved)
    python3 scripts/fetch_arr.py --download    # also save any PDF not already in data/raw/

Decisions: D3 (read the page every run, don't guess file names), D4 (reports from January 2022).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import sys
import time
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

PAGE_URL = "https://www.gaming.nv.gov/about-us/abbreviated-revenue-release-arr/"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
MANIFEST = RAW_DIR / "manifest.csv"
FIRST_REPORT_MONTH = dt.date(2022, 1, 1)  # D4
PAUSE_SECONDS = 1.5  # wait between downloads so we don't overload the state's website
USER_AGENT = "Week 4 casino revenue forecasting project (student research)"


@dataclass
class Report:
    url: str
    filename: str
    released: str          # the page's "Released" column, e.g. "Oct 2026"
    link_label: str        # the page's link text, e.g. "ARR Sep"
    report_month: dt.date  # the month the report covers: the month before release
    flag: str = ""         # set when the page's own labels disagree


class TableReader(HTMLParser):
    """Collects every table on the page: its caption and rows, where each cell keeps its text and first link."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self.table = self.row = self.cell = None
        self.in_caption = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = {"caption": "", "rows": []}
            self.tables.append(self.table)
        elif tag == "caption":
            self.in_caption = True
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": "", "href": None}
            self.row.append(self.cell)
        elif tag == "a" and self.cell is not None and self.cell["href"] is None:
            self.cell["href"] = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag == "caption":
            self.in_caption = False
        elif tag in ("td", "th"):
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table":
            self.table = None

    def handle_data(self, data):
        if self.in_caption and self.table is not None:
            self.table["caption"] += data
        elif self.cell is not None:
            self.cell["text"] += data


def clean(text: str) -> str:
    return " ".join(text.split())


def month_start(text: str) -> dt.date:
    """'Oct 2026' or 'April 2026' -> 1 Oct 2026."""
    return dt.datetime.strptime(f"{text.split()[0][:3]} {text.split()[-1]}", "%b %Y").date()


def report_month_from_label(label: str, released_month: dt.date) -> dt.date:
    """'ARR Sep' released Oct 2026 -> Sep 2026. A label with a year, such as 'ARR Dec 2024', is taken as written."""
    parts = label.split()
    month = dt.datetime.strptime(parts[1][:3], "%b").month
    if len(parts) > 2:
        return dt.date(int(parts[2]), month, 1)
    year = released_month.year
    if dt.date(year, month, 1) >= released_month:
        year -= 1
    return dt.date(year, month, 1)


def find_reports(html: str, first_month: dt.date = FIRST_REPORT_MONTH, last_month: dt.date = dt.date(2100, 1, 1)) -> list[Report]:
    reader = TableReader()
    reader.feed(html)
    reports: list[Report] = []
    seen: set[str] = set()
    for table in reader.tables:
        if "Abbreviated Revenue Release" not in table["caption"]:
            continue
        for row in table["rows"]:
            # Column 1 is the release month; column 2 is the Gaming Win link we need.
            if len(row) < 2 or not (row[1]["href"] or "").lower().endswith(".pdf"):
                continue
            url = urljoin(PAGE_URL, row[1]["href"])
            filename = unquote(Path(urlparse(url).path).name)
            if filename in seen:
                raise RuntimeError(f"Two rows on the page link to the same file: {filename}")
            seen.add(filename)
            released = clean(row[0]["text"])
            label = clean(row[1]["text"])
            released_month = month_start(released)
            report_month = report_month_from_label(label, released_month)
            expected = (released_month - dt.timedelta(days=1)).replace(day=1)  # reports come out the month after
            if report_month < first_month or report_month > last_month:
                continue
            flag = ""
            if report_month != expected:
                flag = f"released '{released}' suggests {expected:%b %Y}, but the file is for {report_month:%b %Y}"
            reports.append(Report(url, filename, released, label, report_month, flag))
    return sorted(reports, key=lambda r: r.report_month)


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def checked_pdf(data: bytes) -> bytes:
    if not data.startswith(b"%PDF"):
        raise ValueError("the link did not return a PDF")
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Find and save the Nevada ARR revenue reports.")
    parser.add_argument("--download", action="store_true", help="save PDFs not already in data/raw/")
    parser.add_argument("--start", default="2022-01", help="first report month, YYYY-MM")
    parser.add_argument("--end", default="2026-09", help="last report month, YYYY-MM")
    args = parser.parse_args()
    first_month = dt.date(*map(int, args.start.split("-")), 1)
    last_month = dt.date(*map(int, args.end.split("-")), 1)
    manifest = MANIFEST if (args.start, args.end) == ("2022-01", "2026-09") else RAW_DIR / f"manifest_{args.start}_{args.end}.csv"

    reports = find_reports(get(PAGE_URL).decode("utf-8", errors="replace"), first_month, last_month)
    if not reports:
        sys.exit("No reports found. The page layout may have changed.")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    checked = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")

    rows = []
    for report in reports:
        dest = RAW_DIR / report.filename
        status = "saved" if dest.exists() else "not saved"
        if args.download and not dest.exists():
            try:
                dest.write_bytes(checked_pdf(get(report.url)))
                status = "downloaded"
            except Exception as exc:
                status = f"failed: {exc}"
            time.sleep(PAUSE_SECONDS)
        exists = dest.exists()
        rows.append({
            "report_month": f"{report.report_month:%Y-%m}", "file": report.filename,
            "page_release": report.released, "page_label": report.link_label, "url": report.url,
            "status": status, "bytes": dest.stat().st_size if exists else "",
            "sha256": sha256(dest) if exists else "", "flag": report.flag, "checked_utc": checked,
        })

    with manifest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    months = [f"{r.report_month:%Y-%m}" for r in reports]
    span = [f"{y}-{m:02d}" for y in range(FIRST_REPORT_MONTH.year, reports[-1].report_month.year + 1)
            for m in range(1, 13) if f"{y}-{m:02d}" <= months[-1]]
    gaps = [m for m in span if m not in months]
    doubles = sorted({m for m in months if months.count(m) > 1})

    print(f"{len(rows)} reports, {rows[0]['report_month']} to {rows[-1]['report_month']}")
    print(f"  months with no report: {', '.join(gaps) or 'none'}")
    print(f"  months with two reports: {', '.join(doubles) or 'none'}")
    for row in rows:
        line = f"  {row['report_month']}  {row['file']:<24} {row['status']}"
        print(line + (f"   CHECK: {row['flag']}" if row["flag"] else ""))
    print(f"\nManifest: {manifest.relative_to(ROOT)}")
    if not args.download:
        print("Listing only. Nothing was downloaded. Run with --download to save the missing PDFs.")


if __name__ == "__main__":
    main()
