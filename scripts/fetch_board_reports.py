"""Find and save the Board's monthly revenue reports (GRI), January 2022 to September 2026.

The Board's Gaming Revenue Information page lists one PDF per month, with link text such as "GRI Aug 2026".
This script reads that page each run, maps each month to its link, and saves any PDF not already present.

    python3 scripts/fetch_board_reports.py               # list only, nothing saved
    python3 scripts/fetch_board_reports.py --download    # also save missing PDFs

Standard library only. Decisions: D2, D3 (read the page every run), D6 (list by default).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

PAGE_URL = "https://www.gaming.nv.gov/about/gaming-revenue/information/"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "board-monthly"
MANIFEST = RAW_DIR / "manifest.csv"
FIRST, LAST = (2022, 1), (2026, 9)  # default range; change with --start / --end
PAUSE_SECONDS = 1.5
USER_AGENT = "Week 4 casino revenue forecasting project (student research)"
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


class LinkReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.href, self.text = [], None, ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.lower().endswith(".pdf"):
                self.href, self.text = href, ""

    def handle_data(self, data):
        if self.href is not None:
            self.text += data

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((" ".join(self.text.split()), self.href))
            self.href = None


def find_reports(html: str, first=FIRST, last=LAST) -> list[tuple[str, str]]:
    """Return (YYYY-MM, full URL) for every month in range, from the link text 'GRI Mon YYYY'."""
    reader = LinkReader()
    reader.feed(html)
    found = {}
    for text, href in reader.links:
        m = re.fullmatch(r"GRI ([A-Za-z]+) (\d{4})", text)
        if m and m.group(1)[:3].lower() in MONTHS:
            found.setdefault((int(m.group(2)), MONTHS[m.group(1)[:3].lower()]), urljoin(PAGE_URL, href))
    out = []
    y, m = first
    while (y, m) <= last:
        if (y, m) not in found:
            raise RuntimeError(f"No link on the page for {y}-{m:02d}")
        out.append((f"{y}-{m:02d}", found[(y, m)]))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description="Find and save the Board's monthly revenue reports.")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--start", default="2022-01", help="first month, YYYY-MM")
    parser.add_argument("--end", default="2026-09", help="last month, YYYY-MM")
    args = parser.parse_args()
    first = tuple(map(int, args.start.split("-")))
    last = tuple(map(int, args.end.split("-")))
    manifest = RAW_DIR / (f"manifest_{args.start}_{args.end}.csv" if args.start != "2022-01" or args.end != "2026-09" else "manifest.csv")

    reports = find_reports(get(PAGE_URL).decode("utf-8", errors="replace"), first, last)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    checked = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    rows = []
    for month, url in reports:
        name = unquote(Path(urlparse(url).path).name)
        dest = RAW_DIR / name
        status = "saved" if dest.exists() else "not saved"
        if args.download and not dest.exists():
            try:
                data = get(url)
                if not data.startswith(b"%PDF"):
                    raise ValueError("the link did not return a PDF")
                dest.write_bytes(data)
                status = "downloaded"
            except Exception as exc:
                status = f"failed: {exc}"
            time.sleep(PAUSE_SECONDS)
        exists = dest.exists()
        rows.append({"report_month": month, "file": name, "url": url, "status": status,
                     "bytes": dest.stat().st_size if exists else "",
                     "sha256": hashlib.sha256(dest.read_bytes()).hexdigest() if exists else "",
                     "checked_utc": checked})
    with manifest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"{len(rows)} reports, {rows[0]['report_month']} to {rows[-1]['report_month']}: {counts}")
    print(f"Manifest: {manifest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
