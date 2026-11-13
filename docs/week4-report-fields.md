# What each report contains

Two Nevada Gaming Control Board reports are used. Both are monthly and are described field by field below. The file list for every download is in `docs/week4-report-index.md` and `docs/week4-report-index.csv`.

---

## Report 1: Abbreviated Revenue Release (ARR) – market totals

**What it is:** a two-page press release, published about four weeks after each month ends. It gives the gaming win (what casinos keep from gambling, before costs) for the state and for each market.

**Used for:** `data/clean/monthly_win.csv`, which holds the win for each area and month.

### Page 1: the win table

The header gives the release date, the month, and a sentence with the statewide win and its change from last year.

Each row is one area. Each row has six figures, in dollars:

| Field | Meaning |
|---|---|
| Current period win | Win for the month in the report (for example, September 2026) |
| Same month last year | Win for the same month a year earlier, as shown in this report |
| % change | Change in the month against last year |
| Fiscal year-to-date win | Win from 1 July to the report month (Nevada's fiscal year starts on 1 July) |
| Prior fiscal year-to-date | The same period a year earlier |
| % change (year-to-date) | Change in the year-to-date figure |

**The 20 areas, in the order printed:**

- Statewide
- Clark County, with its markets below: LV Strip, Downtown, North Las Vegas, Laughlin, Boulder Strip, Mesquite, Balance of County
- Washoe County, with: Reno, Sparks, North Lake Tahoe, Balance of County
- South Lake Tahoe
- Elko County, with: Wendover, Balance of County
- Carson Valley Area (a footnote says it covers Carson City, Gardnerville, Minden and other Douglas County areas, not just one town)
- Other

Two rows share the name "Balance of County". The report separates them by their position under the county, so we give each a unique name (for example, "Balance of Clark").

**Important:** the parts add up to their totals. Each county's markets add up to the county, and the counties add up to the statewide figure, within about $1. So the county and statewide rows must not be added to the markets, or the win is counted twice.

**Footnotes:** "Win totals reflect the most recent data available and are subject to revision." Figures can be revised in later reports (see the revision section below).

### Page 2: tax collections (not used)

Percentage fee collections are the tax casinos pay on their win. The page shows the statewide amount collected each month and the fiscal year-to-date. It is not split by market, so it is not used in the models.

### Data notes for ARR

- **Format changes over time.** Reports from 2015 to 2019 use the same columns, but the wording and layout are slightly older. All 60 of those reports parse to the same 20 rows, with totals that add up.
- **January 2025 is a picture.** Its table on page 1 is an image, not text. We read it with OCR and checked it against the following year's report.
- **Two rows are labelled "Jan 2025".** On the Board's page, one of the links is for the November 2024 report, not December. We read the month from the label, and flag the mismatch.
- **Revisions.** About half of the figures change in a later report, mostly by small amounts (see `docs/week4-revision-review.md`).

---

## Report 2: Monthly Revenue Report (Gaming Revenue Information, GRI) – game-type detail

**What it is:** a longer report, about 48 pages, published each month. It has the win for each area split by type of game. The Board labels the win amounts "in thousands".

**Used for:** `data/clean/game_types_monthly.csv`, which holds the split for each area and month.

### Front page: contents

A list of every area and revenue band, with its page number. The areas include the statewide total, each county and market, and the revenue bands ($1 million and over, and ranges within the Strip and Reno). The Strip is on pages 12 to 20 and Reno on pages 33 to 37 in the August 2026 report.

### Each area page

Each area has three side-by-side blocks of figures:

| Block | Period |
|---|---|
| Current month | The report month (for example, August 2026) |
| Three months | The last three months, to the report month |
| Twelve months | The last twelve months, to the report month |

Each block has five figures:

| Field | Meaning |
|---|---|
| Locations (# of loc) | Number of venues reporting that game |
| Units (# of units) | Number of tables or machines |
| Win amount | Win for the period, in thousands of dollars |
| % change | Change against the same period last year |
| Win percent | For games, win as a share of the amount bet. For slots, win as a share of the amount played |

### The game lines

**Table, counter and card games:** Twenty One (blackjack), Craps, Roulette, Ultimate Texas Hold'em, 3-Card Poker, Baccarat, Mini-Baccarat, Keno, Bingo, Let It Ride, Pai Gow, Pai Gow Poker, Race Book, Sports Pool, Card Games, Other, and a Total.

**Slot machines:** by coin or note size, 1 cent, 5 cent, 25 cent, 1 dollar, 5 dollars, 25 dollars, 100 dollars, Multi Denomination, Other, and a Total. The 2015 reports also show a Megabucks line.

**Total gaming:** table games plus slots (plus card games, for the older layout). It matches the ARR win for the same area and month.

### Lines that are not added to totals

- **Race Book (1):** the footnote shows it is the parimutuel race book.
- **Sports Pool (2):** this is the sports betting line. Its sub-lines (football, basketball, baseball, parlay cards, hockey) are detail only.
- **Sports – Mobile:** marked with three stars. It is a memo line showing mobile sports wagering, not an extra amount.

### Data notes for the Monthly Revenue Report

- **Sports betting is inside the gaming win.** So adding it on top would count it twice. We use it as an input instead.
- **Blank games.** Some games have no win in a month (for example, Bingo or $25 slots in some Reno months). We record those as 0, and the totals confirm it.
- **The older layout (2015 to 2019)** uses upper-case headings, bars between the columns, and "Total Games & Tables" for the table total. The parser handles both layouts.
- **A summary row can disagree.** The last page of the May, June and July 2025 reports has a summary table whose Strip figure does not match the detail page. For example, May's summary shows $625.7m against $713.8m on the detail page, which matches the ARR. We use the detail pages only.
- **September 2017.** The Board's detail page matches the later revised ARR figure, not the first-published one. The difference is about 0.1%.

---

## Quick reference: which report feeds which table

| Table | Source report | Level of detail |
|---|---|---|
| `data/clean/monthly_win.csv` | ARR, page 1 | 20 areas a month, 117 months (2015 to 2019, and 2022 to 2026) |
| `data/clean/game_types_monthly.csv` | GRI, area pages | Each game and slot type, for statewide, the Strip and Reno, 117 months |
| `data/features/features_strip_reno.csv` | Both (derived) | Lags, averages, changes, shares and calendar, for the Strip and Reno |
