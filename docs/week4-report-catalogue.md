# Report catalogue: one entry for each distinct report

The project holds 234 Board reports: 117 ARR and 117 Monthly Revenue Reports (GRI), covering January 2015 to September 2026, without 2020 and 2021. Grouped by layout, they come in **six distinct formats**: two ARR and four GRI. Each format is described once below, with one example file you can open.

The grouping comes from `scripts/catalogue_reports.py`. The format of every individual report is in `docs/week4-report-catalogue.csv`.

---

## ARR: Abbreviated Revenue Release (market totals)

### Format A1: ARR, standard — 116 reports

- **Months:** January 2015 to September 2026, except January 2025.
- **Example to open:** `data/raw/mrrsept2026.pdf` (2 pages, 253 KB). Online: https://www.gaming.nv.gov/siteassets/content/about/abb-revenue/mrrsept2026.pdf
- **What it is:** a two-page press release with the gaming win for the state and each market.
- **Page 1, the win table.** 20 areas: statewide, 3 counties, the markets inside them, South Lake Tahoe, Carson Valley and Other. For each area, six figures in dollars:
  - Win for the month
  - Win for the same month last year
  - % change
  - Fiscal year-to-date win (from 1 July)
  - Prior fiscal year-to-date win
  - % change
- **Page 2, tax collections.** The statewide percentage fee (tax) collected each month and year to date. It isn't split by market.
- **What we use:** page 1, the month's win and the same month last year, which go into `data/clean/monthly_win.csv`. Page 2 isn't used.

### Format A2: ARR, table as a picture — 1 report

- **Month:** January 2025.
- **Example to open:** `data/raw/2025Jan-arrevenue.pdf` (2 pages, 145 KB). Online: https://www.gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/abb-revenue/2025Jan-arrevenue.pdf
- **What's different:** it has the same fields as A1, but the page 1 table is an image, not text. Only the heading and the opening sentence are readable as text.
- **How we handled it:** we read the table with OCR (reading text from an image). The figures were checked against the same month in the January 2026 report, and the totals add up.

---

## GRI: Monthly Revenue Report (win by game type)

All four GRI formats contain the same information. For each area and revenue band, they show the win for each game type and slot size. Each figure has three blocks: the current month, the last three months and the last twelve months. Each block has the number of locations, the number of tables or machines, the win (in thousands of dollars), the % change and the win percentage.

### Format G1: GRI, older layout — 38 reports

- **Months:** January 2015 to April 2018, except February 2015 and September 2017.
- **Example to open:** `data/raw/board-monthly/2015Jan-gri.pdf` (48 pages, 509 KB). Online: https://www.gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/2015Jan-gri.pdf
- **Layout:** names in capitals ("TWENTY-ONE", "SLOT MACHINES"), with bars between the columns.
- **Game lines:** Twenty-One, Craps, Roulette, 3-Card Poker, Baccarat, Mini-Baccarat, Keno, Bingo, Let It Ride, Pai Gow, Pai Gow Poker, Race Book, Sports Pool and Other, then Card Games.
- **Slot lines:** 1 cent, 5 cent, 25 cent, 1 dollar, Megabucks, 5 dollar, 25 dollar, 100 dollar, Multi Denomination and Other.
- **Totals:** "TOTAL GAMES", "TOTAL SLOT MACHINES" and "TOTAL GAMING WIN".
- **A change inside this format, from July 2015:** the table total is renamed "TOTAL GAMES & TABLES" and now includes card games. Before July 2015, card games sat outside it.
- **Sports detail:** below the totals, a breakdown of sports betting by sport (football, basketball, baseball, parlay cards, other). It's detail only, not added to the totals.

### Format G2: GRI, older layout with a page missing — 1 report

- **Month:** February 2015.
- **Example to open:** `data/raw/board-monthly/2015Feb-gri.pdf` (47 pages, 504 KB). Online: https://www.gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/2015Feb-gri.pdf
- **What's different:** the same layout as G1, but one page is missing: the Strip's "$12 million to $36 million revenue range" page.
- **Effect on us:** none. We use only the "All Nonrestricted Locations" pages, which are all present.

### Format G3: GRI, current layout — 76 reports

- **Months:** September 2017, then May 2018 to September 2026, except June and July 2025.
- **Example to open:** `data/raw/board-monthly/monthly-revenue-report---august-2026.pdf` (48 pages, 463 KB). Online: https://www.gaming.nv.gov/siteassets/content/about/gaming-revenue/monthly-revenue-report---august-2026.pdf
- **Layout:** names in normal case, with section headings "Table, Counter and Card Games" and "Slot Machines", and "Total" and "Total Gaming" lines.
- **Game lines:** as G1, plus Ultimate Texas Hold'em. Card Games is inside the table total.
- **Slot lines:** as G1, but without Megabucks.
- **Memo lines below the totals:** Race Book Parimutuel, Sports – Mobile (mobile sports betting), and sports by type. These are detail only.
- **One oddity:** September 2017 is in this layout, while October 2017 to April 2018 are still in the older one. Its figures match the Board's later revised totals, not the first-published ones. It may have been reissued, but I can't confirm that from the file.

### Format G4: GRI, current layout with unreadable front pages — 2 reports

- **Months:** June and July 2025.
- **Example to open:** `data/raw/board-monthly/2025jun-gri.pdf` (48 pages, 14 MB). Online: https://www.gaming.nv.gov/siteassets/content/about/gaming-revenue/2025jun-gri.pdf
- **What's different:** the files are about 30 times larger than normal. The cover and contents pages have no readable text, and the section headings are missing from the area pages. The figures themselves are still readable, and the area totals match the ARR.
- **A known problem:** the summary table on the last page shows Strip figures that disagree with the detail pages. The same problem appears in May 2025, which is otherwise a G3 report. We use the detail pages only.

---

## Summary

| Format | Report | Count | Months | Example file |
|---|---|---|---|---|
| A1 | ARR, standard | 116 | Jan 2015 – Sep 2026, except Jan 2025 | `data/raw/mrrsept2026.pdf` |
| A2 | ARR, table as a picture | 1 | Jan 2025 | `data/raw/2025Jan-arrevenue.pdf` |
| G1 | GRI, older layout | 38 | Jan 2015 – Apr 2018, except Feb 2015 and Sep 2017 | `data/raw/board-monthly/2015Jan-gri.pdf` |
| G2 | GRI, older layout, page missing | 1 | Feb 2015 | `data/raw/board-monthly/2015Feb-gri.pdf` |
| G3 | GRI, current layout | 76 | Sep 2017, May 2018 – Sep 2026, except Jun–Jul 2025 | `data/raw/board-monthly/monthly-revenue-report---august-2026.pdf` |
| G4 | GRI, current layout, unreadable front pages | 2 | Jun – Jul 2025 | `data/raw/board-monthly/2025jun-gri.pdf` |
