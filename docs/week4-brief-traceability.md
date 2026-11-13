# Week 4 brief: what we have done, bullet by bullet

Each line of the brief is quoted in bold and numbered, followed by its status, the specifics (which reports, which model, which forecast, how), the evidence, and what is still to do. Decision numbers (D1, D2 ...) refer to `docs/week4-decision-log.md`.

Status key: **Done** · **Partly** · **Not started**

---

## Summary for the call

### Where each part of the brief stands

| Brief section | Status | In one line |
|---|---|---|
| Scenario, dataset, markets | Mostly done | Board data for four markets. Models built for the Strip and Reno only |
| Business questions | Mostly done | All seven answered and monitored monthly. Still missing: a range around each forecast |
| Step 1: Prepare the data | Mostly done | 234 reports, four clean tables, 14 features. Gaps: source and derived not split in one table, no single preparation document |
| Step 3: Baseline | Done | "Same month last year" and "last published". Gap: moving-average baseline |
| Step 4: Models | Done | Seven models. LSTM left out by choice (D42) |
| Step 5: Backtesting | Done | 43 months, 774 forecasts, two months ahead, no peeking |
| Step 6: Evaluation | Mostly done | MAE, RMSE, MAPE and timings for all. Gap: training and prediction time not separated |
| Step 7: MLflow tracking | Done | 18 runs with settings, measures, charts and models (D46) |
| Step 8: Model selection | Done | Baseline chosen and approved (D28) |
| Step 9: MLflow registry | Done | Strip V1 production. Reno V1 challenger, V2 production (D46) |
| Step 10: Champion and Challenger | Done | Rule checked every month. Reno V2 in production from November 2026 (D36, D45). The Strip stays on V1 |
| Step 11: Observability | Done | Monthly monitoring built and replayed. Both markets Healthy (data to Sep 2026) |
| Step 12: Data quality monitoring | Done | Checks run before every forecast. Tested on a broken month |
| Step 13: Drift | Done | Fast, slow and capacity alerts run monthly |
| Step 14: Retraining | Done | Monthly retraining runs in monitoring. Yearly and alert-triggered reviews |
| Step 15: Dashboard | Done | Streamlit, on your computer, both markets (D47) |
| Step 16: Product decisions | Done | All seven 'explain' points decided (D28, D31 to D34, D38 to D40) |
| Step 17: Risks | Partly | All seven risks seen in our project. Register to write |
| Step 18: Deliverables | All 15 done | See the Step 18 table |

### Decisions (all ten made on 12 November 2026)

1. ~~The promotion rule~~: **decided (D32), with the way back (D33)**. Reno switch approved, effective once monitoring runs (D36)
2. ~~The named Challengers~~: **decided (D41)**
3. ~~Which measure matters most~~: **decided (D31)**: MAPE headline, RMSE guard, bias tracked, MAE for finance
4. ~~What happens when data is incomplete~~: **decided (D38)**: exclude the month, fall back, alert. Repairs only if all checks pass. Late alert after 7 days
5. ~~The drift rule~~: **decided (D37)**: fast, slow and capacity alerts. Bias and hold shown, not alerted
6. ~~The retraining policy~~: **decided (D39)**: monthly routine retraining, plus a yearly review and a review on alerts
7. ~~Who approves a replacement~~: **decided (D34)**: the Product Owner, after an evidence pack, with Finance consulted. Emergency fallback to the simple model is allowed
8. ~~LSTM~~: **not tried, by choice (D42)**
9. ~~GitHub~~: **public, created (D43, D49)**
10. ~~Dashboard~~: **on your computer first (D44)**

### Corrections made on 12 November 2026, while checking against the brief

1. Random Forest and XGBoost first trained without adding new months. Fixed and rerun. They still don't beat the baseline (5.3).
2. "No model beats the baseline on the Strip" is true for MAE and MAPE, but not RMSE. Corrected (6.8).
3. The note in `data/clean/build_checks.md` says only the last 12 months are unrevised. 2019 is too (1.8d). Not yet corrected in that file.

---

## Reference: the reports, the forecast and the models

These are referred to throughout.

### The two reports

| | Report 1: Monthly Revenue Release ("ARR") | Report 2: Monthly Revenue Report ("GRI") |
|---|---|---|
| Publisher | Nevada Gaming Control Board | Nevada Gaming Control Board |
| Web page | gaming.nv.gov/about-us/abbreviated-revenue-release-arr/ (the brief's link) | gaming.nv.gov/about/gaming-revenue/information/ |
| What it is | A 2-page press release, one per month | A report of about 48 pages, one per month |
| What it gives | Gaming win (what casinos keep from gambling) for the month, the same month last year, and the year to date, for the state and 20 areas, in dollars | The win split by game (blackjack, baccarat, craps, slots by coin size, sports betting ...), plus the number of venues, tables and machines, and the "hold" (the share of money bet that the casino keeps), in thousands of dollars |
| Months held | Jan 2015 to Sep 2026, without 2020 and 2021: 117 reports | The same 117 months |
| Example | `data/raw/mrrsept2026.pdf` | `data/raw/board-monthly/monthly-revenue-report---august-2026.pdf` |
| Becomes | `data/clean/monthly_win.csv` | `data/clean/game_types_monthly.csv`, `data/clean/capacity_hold_monthly.csv` |

### What is forecast

- **The number:** the gaming win for one market for one month, in dollars. For example, the LV Strip in September 2026 was $693,467,182.
- **The markets:** the LV Strip and Reno (models built), plus Downtown and Laughlin (to be built, D29).
- **How far ahead:** two months. The Board publishes each month about four weeks after it ends. In late October we have September's figure, so the forecast is for November (D19).

### The models tested

| Model | How it forecasts a month |
|---|---|
| **Same month last year** (the baseline, now the production model) | Uses the same month a year earlier. A forecast for November 2026 is November 2025's figure: $784.3m for the Strip, $55.6m for Reno |
| **Last published** (second baseline) | Uses the newest figure available, two months back |
| **ARIMA** | A statistical model that learns from the market's own recent months |
| **Seasonal ARIMA** | ARIMA plus a yearly pattern that repeats every 12 months |
| **Seasonal ARIMA + calendar** | Also uses days in the month, Friday and Saturday nights, and public holidays |
| **Seasonal ARIMA + game mix** | Also uses the share of win from slots and from sports betting, two months back |
| **Seasonal ARIMA + both** | Calendar and game mix together |
| **Random Forest** | A machine-learning model of many decision trees, using 12 inputs (recent figures, averages, changes, game mix, calendar) |
| **XGBoost** | A machine-learning model of trees built one after another, using the same 12 inputs |

### How they were tested

- **Test period:** 43 months, March 2023 to September 2026.
- **Each month, each model is rebuilt** using only figures published by then, exactly as if it had been running at the time. Training data: 2015 to 2019 and 2022 onward. 2020 and 2021 are left out because of the COVID closures (D23).
- **Each forecast is scored** against the Board's newest figure for that month.
- **Measures:**
  - MAPE: the average miss as a percentage.
  - MAE: the average miss in $ millions.
  - RMSE: like MAE, but large misses count for more.
- **Example:** for the Strip in September 2026, the baseline forecast $687.8m (September 2025's figure). The actual was $693.5m, a miss of 0.8%. For Reno in August 2026, it forecast $68.7m against an actual of $79.4m, a miss of 13.5%.

---

## Business scenario and purpose

**0.1 "A casino industry analytics team receives monthly gaming revenue data from different Nevada casino markets."**
- **Status:** Done
- **Specifics:** We hold 234 of the Board's monthly reports: 117 monthly releases and 117 Monthly Revenue Reports, covering January 2015 to September 2026, without 2020 and 2021.
- **How:** Two scripts read the Board's web pages, list the reports found, and download them with your approval. Each file's size and fingerprint are recorded.
- **Evidence:** `scripts/fetch_arr.py`, `scripts/fetch_board_reports.py`, `docs/week4-report-index.md`

**0.2 "Management … want to understand what revenue can be expected in the coming month, which forecasting model should be trusted, whether the model is still performing well, and when it should be retrained."**
- **Status:** Partly
- **Specifics:**
  - The coming month: the approved forecast is "same month last year", two months ahead.
  - Which model to trust: tested (0.9 below).
  - Still performing well: not started.
  - When to retrain: not started.
- **Still to do:** Steps 11 (monitoring), 13 (drift), 14 (retraining)

**0.3 "The purpose of this project is to build a complete machine learning lifecycle around casino revenue forecasting."**
- **Status:** Partly
- **Specifics:**
  - Done: getting the data, cleaning it, creating features, building nine models and baselines, and testing them over 43 months.
  - Not started: MLflow tracking, the model registry, monitoring, drift, retraining, and the dashboard.

**0.4 "The project should cover model comparison, experiment tracking, model registration, monitoring, drift detection, and retraining decisions."**
- **Status:** Partly
- **Specifics:**
  - Model comparison: done (`docs/week4-model-comparison.md`).
  - Experiment tracking: not started (Step 7).
  - Model registration: not started (Step 9).
  - Monitoring: not started (Step 11).
  - Drift detection: not started (Step 13).
  - Retraining decisions: not started (Step 14).

---

## Dataset

**0.5 "Use the official Nevada Gaming Control Board revenue data."**
- **Status:** Done
- **Specifics:**
  - The monthly release gives the market totals that we forecast.
  - The Monthly Revenue Report gives the game-by-game detail, venue counts, table and machine counts, and hold.
  - Both are the Board's own publications.
- **Evidence:** `docs/week4-report-catalogue.md` (six layouts across the years, one example of each)
- **Decisions:** D1, D16

**0.6 "Monthly Revenue Release: https://www.gaming.nv.gov/about-us/abbreviated-revenue-release-arr/"**
- **Status:** Done
- **How:** `scripts/fetch_arr.py` reads this page each time. Each row links one month's PDF (for example "ARR Sep" released Oct 2026). The script works out the month from the link, lists what's missing, and downloads only with `--download`. Two checks: no month missing, and no month listed twice.
- **Found:** two links on the page are both labelled "Jan 2025"; one is actually November 2024. The script uses the month in the link text and flags the mismatch (D7).
- **Evidence:** `data/raw/manifest.csv`, `data/raw/manifest_2015-01_2019-12.csv`

**0.7 "Select a few casino markets for the project, such as Las Vegas Strip, Downtown Las Vegas, Reno, or Laughlin."**
- **Status:** Partly
- **Specifics:**

  | Market | Share of state win (2025) | Monthly win, Jan 2025 to Sep 2026 | Month-to-month swing | Models |
  |---|---|---|---|---|
  | LV Strip | 55.8% | $647m to $840m | 12% | Built |
  | Reno | 5.0% | $56m to $82m | 12% | Built |
  | Downtown | 6.0% | $62m to $103m | 18% | Not yet |
  | Laughlin | 3.1% | $34m to $50m | 16% | Not yet |
- **Why these:** the Strip and Reno came first, because they're the largest and steadiest (D14). Downtown and Laughlin were added to show how forecasts behave in noisier markets (D29).
- **Still to do:** features and models for Downtown and Laughlin

---

## Main business questions

**0.8 "What revenue should we expect next month?"**
- **Status:** Mostly done
- **Specifics:** monitoring makes the forecast two months ahead each month, from each market's production model (D19, D45). With data to September 2026, the forecasts for November 2026 are:
  - Strip: **$784.3m** (V1, "same month last year").
  - Reno: **$64.4m** (V2, Seasonal ARIMA + game mix).
- **Still to do:** show a range with each forecast. On the test, the Strip's typical miss was about 4% and a bad month over 12%. For Reno, about 7% and over 11%.

**0.9 "Which forecasting model performs best?"**
- **Status:** Done for the Strip and Reno
- **Specifics:** average miss over 43 months, two months ahead:

  | Model | Strip MAPE | Strip MAE ($m) | Reno MAPE | Reno MAE ($m) |
  |---|---|---|---|---|
  | Same month last year | **5.8%** | **43.6** | **7.2%** | 4.8 |
  | Seasonal ARIMA + both | 6.1% | 45.7 | 7.8% | 5.0 |
  | Seasonal ARIMA + calendar | 6.3% | 46.5 | 8.1% | 5.2 |
  | Random Forest | 6.7% | 50.0 | 7.5% | 4.9 |
  | XGBoost | 7.1% | 52.3 | 7.9% | 5.2 |
  | Seasonal ARIMA | 6.6% | 49.0 | 9.5% | 6.0 |
  | Seasonal ARIMA + game mix | 6.7% | 49.9 | **7.2%** | **4.7** |
  | ARIMA | 7.8% | 58.1 | 10.9% | 7.0 |
  | Last published | 10.4% | 76.7 | 11.5% | 7.2 |
- **Why the simple rule wins:** the seasonal pattern is the main signal, and repeating last year's month captures it. The more complex models had only about 8 years of usable history to learn from.
- **Evidence:** `data/model/model_comparison.md`, `docs/week4-model-comparison.md`
- **Decisions:** D26, D27, D28

**0.10 "Is the current production model still reliable?"**
- **Status:** Done
- **Specifics:** answered every month by monitoring (Step 11). Latest run (data to September 2026): both markets are **Healthy**.
  - Strip: 12-month MAPE 5.39%.
  - Reno: 6.76%.

**0.11 "Has the behaviour of a casino market changed over time?"**
- **Status:** Done (D48), and watched monthly by the drift alerts (D37)
- **Specifics:**
  - Markets reset 25–40% higher after COVID. Laughlin is the exception, at −4%.
  - Growth has stalled since 2023, except in Reno (+8% in 2026).
  - The Strip's December peak has strengthened (1.08 to 1.18 of an average month).
  - Slot machines are down 20–25%, each earning about twice as much.
  - Strip misses track baccarat luck (correlation 0.75).
- **Evidence:** `docs/week4-exploratory-analysis.md`

**0.12 "Is the latest prediction error acceptable?"**
- **Status:** Done (D31, D37), checked every month
- **Specifics:**
  - A month's miss is acceptable unless it's in the worst 10% of the model's history (Strip over 12.4%, Reno over 11.1%).
  - Two such months in three, or a 12-month MAPE more than 1.5 points above normal, turns the market's status to **Investigate**.
  - The monthly monitoring that checks this each month isn't built yet.

**0.13 "When should the model be retrained?"**
- **Status:** Done (D39). Retraining runs every month in monitoring.
- **Specifics:**
  - Models that learn settings re-learn them every month.
  - A full review happens once a year, and on a slow alert, a real capacity change, or a fast alert with a lasting cause.
  - "Same month last year" has nothing to retrain.

**0.14 "Should a new model replace the current production model?"**
- **Status:** Done
- **Specifics:**
  - The promotion rule (D32, D33) runs every month in monitoring.
  - Reno's Challenger met it, and the Product Owner approved the switch (D36). Reno V2 is in production from the November 2026 forecast (D45).
  - The Strip's Challenger doesn't meet it, so the Strip stays on V1.
- **Decisions:** D28, D32, D33, D36, D45

---

## Step 1: Prepare the data

**1.1 "Download the historical revenue reports from the Nevada Gaming Control Board."**
- **Status:** Done
- **Specifics:**
  - 117 monthly releases (2 pages each, 23 MB in total).
  - 117 Monthly Revenue Reports (47 to 48 pages each, 82 MB in total).
  - Both cover January 2015 to December 2019 and January 2022 to September 2026.
- **How:**
  - `scripts/fetch_arr.py` and `scripts/fetch_board_reports.py` read the Board's pages each run. They list every report from the link text (for example "GRI Aug 2026"), compare the list with what's already saved, and download only with `--download`, pausing between files.
  - Each file is checked to be a real PDF. Its size and fingerprint (SHA-256) go in a manifest.
  - You approved each batch: 2022 to 2026 (D8, D16) and 2015 to 2019 (D22).
- **Not held:** 2020 and 2021, which were left out because of the COVID closures (D23).
- **Evidence:** `docs/week4-report-index.md`, `docs/week4-report-index.csv`

**1.2 "Extract the available information from the reports and convert it into a structured dataset that can be used for forecasting."**
- **Status:** Done
- **How:**
  - Every monthly release is read by two separate methods, a text reader (`pdftotext`) and `pdfplumber`, and every number is compared between them. All numbers agree (D10, D11).
  - The January 2025 table is a picture, so it was read with OCR.
  - Each market's figures must add up to its county, and the counties to the statewide total, within $10.
- **Result, four tables:**

  | Table | Rows | One row is | From |
  |---|---|---|---|
  | `data/clean/monthly_win.csv` | 2,340 | One area in one month (20 areas × 117 months) | Monthly release |
  | `data/clean/game_types_monthly.csv` | 9,551 | One game or slot type, for one area in one month (statewide, Strip, Reno) | Monthly Revenue Report |
  | `data/clean/capacity_hold_monthly.csv` | 585 | One area in one month: venues, tables, machines and hold (statewide, Strip, Downtown, Laughlin, Reno) | Monthly Revenue Report |
  | `data/features/features_strip_reno.csv` | 86 | One market in one test month, with its 14 inputs | Built from the tables above |
- **Decisions:** D13, D17, D24, D25, D30

**1.3 "The student should first understand what information is actually available in the source reports before creating the final dataset."**
- **Status:** Done
- **How:** We read the September 2026 release line by line together before building anything. Later we grouped all 234 reports by layout to find every format.
- **Found:**
  - Six distinct layouts: two for the monthly release, four for the Monthly Revenue Report (`docs/week4-report-catalogue.md`).
  - The full field list, saying which fields we use (`docs/week4-report-fields.md`).
  - Page 2 of the monthly release (the tax collected) covers the whole state only, so it isn't used.
  - The Monthly Revenue Report also gives venue counts, table and machine counts, and hold. These were missed at first and found in the review (D30).

**1.4 "Keep the original source information separate from any fields created during data preparation."**
- **Status:** Partly
- **Specifics:**

  | Table | Source fields (printed in a report) | Fields we created | Separate? |
  |---|---|---|---|
  | `capacity_hold_monthly.csv` | All | None | Yes |
  | `game_types_monthly.csv` | game, win | section (table/slot), win changed from thousands to dollars | Mostly |
  | `monthly_win.csv` | gaming_win, first_published, source_file | parent, level, unique names such as "Balance of Clark", source_basis, revised, revision_pct | **No**, they sit side by side |
  | `features_strip_reno.csv` | target_win_latest | Every other column, each starting `derived_` | Yes |
- **Still to do:** split `monthly_win.csv` into a source table and a derived table

**1.5 "After extracting the source data, create any additional features that are required for forecasting."**
- **Status:** Partly
- **Specifics:** 14 inputs for the LV Strip and Reno, March 2023 to September 2026 (86 rows). Each one uses only figures published two months or more before the month forecast (D18, D19).
- **Still to do:**
  - The same inputs for Downtown and Laughlin (D29).
  - New inputs from the venue, table, machine and hold data (D30), not yet tested.

**1.6 "These may include historical lag values, previous period values, moving averages, percentage changes, seasonal indicators, or other useful time series features."**
- **Status:** Done
- **Specifics:**

  | Brief's example | Our input | What it is |
  |---|---|---|
  | Historical lag values | `derived_same_month_last_year_win` | The win 12 months before |
  | Previous period values | `derived_last_published_win` | The newest published win, two months before |
  | Moving averages | `derived_avg3_last_published`, `derived_avg12_last_published` | Average of the 3 and 12 newest months |
  | Percentage changes | `derived_yoy_change_last_published`, `derived_mom_change_last_published` | Change on a year ago, and on the month before |
  | Seasonal indicators | `derived_month_of_year` | 1 to 12 |
  | Other useful features | `derived_days_in_month`, `derived_weekend_days`, `derived_friday_saturday_nights`, `derived_federal_holidays` | Calendar for the month forecast |
  | Other useful features | `derived_last_published_slot_share`, `..._table_share`, `..._sports_pool_share` | Share of win from slots, tables and sports betting |

**1.7 "Any calculated or engineered feature should be clearly identified as a derived feature and should not be presented as an original field from the source data."**
- **Status:** Partly
- **Specifics:**
  - Done in the feature table and the calendar table (`data/features/calendar.csv`, 144 months): every created column starts with `derived_`.
  - Not done in `monthly_win.csv`, where parent, level, revised and revision_pct aren't marked.
- **Still to do:** the same split as 1.4

**1.8 "Document the data preparation process so it is clear:"**
- **Status:** Partly
- **Specifics:** each point below is covered, but in several files. There's no single data-preparation document.
- **Still to do:** write `docs/week4-data-preparation.md`, with these five headings

**1.8a "What information came directly from the source reports"**
- **Status:** Partly
- **Where it is now:** `docs/week4-report-fields.md` (every field, and whether it's used)
- **In short:**
  - From the monthly release: the win for the month and the same month last year, for 20 areas.
  - From the Monthly Revenue Report: the win by game and slot type, venue counts, table and machine counts, and hold.

**1.8b "What information was calculated during preprocessing"**
- **Status:** Partly
- **Where it is now:** the decision log (D7, D9, D13)
- **In short:**
  - The month each report covers, taken from the link label.
  - Which figure counts: the newest published (D9).
  - The revised flag and the % revision.
  - The county and market grouping, with unique "Balance of" names.
  - Win converted from thousands to dollars.

**1.8c "What features were created for model training"**
- **Status:** Partly
- **Where it is now:** `data/features/feature_checks.md` and 1.6 above

**1.8d "What data quality issues were found"**
- **Status:** Partly
- **Where it is now:** `data/extracted/cross_check.md`, `docs/week4-revision-review.md`, `docs/week4-report-catalogue.md`, the decision log
- **Found:**
  1. Two links on the Board's page are both labelled "Jan 2025", and one is really November 2024 (D7).
  2. The January 2025 table is a picture, not text.
  3. Figures change after first publication. 950 of 1,860 checkable figures changed, 23 by more than 1%, all small areas (D12, D24).
  4. In May, June and July 2025, the Monthly Revenue Report's last-page summary shows the wrong Strip figure (D16).
  5. The September 2017 Monthly Revenue Report matches the revised totals, not the first-published ones (D25).
  6. June and July 2025 files are about 30 times the normal size, and their front pages can't be read (D30).
  7. February 2015 is missing one page: the Strip's $12–36 million band.
  8. The report layout changed three times: in July 2015, in September 2017 and in May 2018.
  9. The venue count changed meaning in 2018, from "locations" to "licensees" (D30).
  10. Some games are blank in some months, and baccarat isn't shown where fewer than three venues offer it.
  11. Footnote stars in area names, and "Balance of County" used three times.
  12. Figures for 2019 and for October 2025 to September 2026 haven't been revised yet. For 2019, that's because we don't hold the 2020 reports. (The note in `data/clean/build_checks.md` names only the last 12 months and needs correcting.)

**1.8e "How missing or inconsistent data was handled"**
- **Status:** Partly
- **In short, numbered as in 1.8d:**
  1. The month is read from the link text, and the mismatch is flagged.
  2. Read with OCR, then checked against the January 2026 report and the totals.
  3. The newest figure is used. The 23 big revisions were checked against the year-to-date figures and confirmed as genuine.
  4. Only the detail pages are used.
  5. The page is matched to the revised figure, and this is logged.
  6. The figures are still read. The missing venue count is left blank.
  7. No effect: we use only the "All Nonrestricted Locations" pages.
  8. The reader handles every layout.
  9. Not to be used as one series across 2018.
  10. Blank games are recorded as 0, and the totals confirm it.
  11. Stars removed, and the names made unique.
  12. Marked by the `revised` flag.

  Also: **2020 and 2021 are excluded** from training (D23).

**1.9 "The final dataset should be suitable for time series forecasting and should preserve the correct chronological order of the data."**
- **Status:** Done for the Strip and Reno
- **Specifics:**
  - One row per area per month, sorted by month.
  - All 20 areas present in every one of the 117 months.
  - The only gap is the deliberate one for 2020 and 2021.
  - The feature table holds one row per market per month, in order, March 2023 to September 2026.

**1.10 "Do not randomly split the data because future information should not be used to predict past periods."**
- **Status:** Done
- **How:**
  - No random split anywhere.
  - Each test month is forecast by a model trained only on months published two months or more earlier.
  - Its inputs use first-published figures, as known at the time, not later revisions.
  - As a check, rebuilding the baseline from the feature table gives exactly the same results as the separate baseline test (5.75% Strip, 7.24% Reno).

---

## Step 3: Create a baseline model

**3.1 "Start with a simple baseline."**
- **Status:** Done
- **What we did:** two simple rules, with no model and no training:
  - **Same month last year.** The forecast for September 2026 is the figure for September 2025. Strip: $687.8m.
  - **Last published.** The forecast for September 2026 is the newest figure available two months earlier, which is July 2026.
- **Evidence:** `scripts/baseline.py`, `data/model/baseline_backtest.csv`, and the two baseline rows in `data/model/model_comparison.md`

**3.2 "For example, the next month revenue can initially be predicted using the previous month revenue or a moving average."**
- **Status:** Partly
- **Previous month:** can't be used, because when a forecast is made, last month's figure isn't published yet (D19). "Last published", the figure from two months back, is the closest honest version.
- **Moving average:** not tested as a baseline. The 3-month average exists only as a model input.
- **Gap:** add a moving-average baseline, for example the average of the 3 newest published months.

**3.3 "The baseline is important because every advanced model should perform better than a simple approach."**
- **Status:** Done
- **What we did:** every model was scored on the same 43 months as the baselines, and compared against "same month last year" (Step 6).

**3.4 "Do not assume that a complicated model is automatically better."**
- **Status:** Done
- **What we found:** the simplest rule is the most accurate on two of the three measures for the Strip, and ties on Reno. "Last published" is much worse (10.4% against 5.8% on the Strip), because it ignores the seasons. For example, it forecasts December from October, which misses the December peak.

---

## Step 4: Train multiple forecasting models

**4.1 "Train multiple models so their performance can be compared."**
- **Status:** Done
- **The seven models, and exactly how each is set up:**

  | Model | How it works | Settings |
  |---|---|---|
  | ARIMA | Predicts from the market's own recent month-to-month changes | Each month it tries 4 versions and keeps the best fit (by AIC, a score that rewards fit and penalises complexity) |
  | Seasonal ARIMA | As ARIMA, and also links each month to the same month a year earlier | Same 4 versions, plus a 12-month seasonal term |
  | Seasonal ARIMA + calendar | Also uses the calendar for the month forecast | Days in the month, Friday and Saturday nights, federal holidays |
  | Seasonal ARIMA + game mix | Also uses the game mix two months back | Share of win from slots, and from sports betting |
  | Seasonal ARIMA + both | Calendar and game mix | As above |
  | Random Forest | 300 decision trees, each predicting this month's change against the same month last year. The answer is their average | 12 inputs. At least 2 months in each leaf |
  | XGBoost | 200 small trees built in sequence, each correcting the last | 12 inputs. Depth 3, learning rate 0.05, 80% of rows and inputs sampled per tree |
- **The 12 inputs for the tree models:** last published win, same month last year, 3- and 12-month averages, year-on-year change, month-on-month change, slot share, sports-pool share, month of year, days in the month, Friday and Saturday nights, federal holidays.
- **Evidence:** `scripts/compare_models.py`, `scripts/tree_models.py`. The earlier, shorter runs (`scripts/arima_backtest.py`, `scripts/sarima_features.py`) are superseded.

**4.2 "You can select models such as ARIMA, XGBoost, Random Forest, or LSTM."**
- **Status:** Done. Three of the four, and LSTM left out by recorded choice (D42)
- **Specifics:** ARIMA, XGBoost and Random Forest are done. LSTM wasn't tried.
- **Why not LSTM:** it's a neural network that needs far more data than we have, and a large extra install.
- **Decided (D42):** not tried, by choice. It needs far more data than we have, a large install, and the tree models already struggled with this little data.

**4.3 "At least two models should be compared with the baseline."**
- **Status:** Done
- **Specifics:** seven models compared with two baselines.

**4.4 "The objective is not to use the most complicated model."**
- **Status:** Done
- **Specifics:** the recommended model is the simplest one tested (D28).

**4.5 "The objective is to select the most suitable model for the business problem."**
- **Status:** Done
- **Specifics:** "same month last year" was chosen as accurate, explainable in one sentence, and with nothing to maintain (D28, Step 6.9).

---

## Step 5: Use time based backtesting

**5.1 "Use historical backtesting instead of a random train and test split."**
- **Status:** Done
- **Specifics:** no random split anywhere. The test replays the past month by month.

**5.2 "For example, train the model using historical months and predict the next month."**
- **Status:** Done, two months ahead
- **Example:** to forecast September 2026, the models are trained on figures up to July 2026, because that's the newest the Board had published. They then predict September.

**5.3 "Then move the training window forward and predict the following month."**
- **Status:** Done
- **Specifics:** for October 2026, they're retrained with August 2026 added, and so on. The training data always starts in January 2015 and grows by one month each time. 2020 and 2021 are left out.
- **Mistake found and fixed (12 Nov 2026):** Random Forest and XGBoost first trained on the same 46 months (2016 to 2019) in every test month, because of an error in `scripts/tree_models.py`. Fixed and rerun: their training data now grows from 46 months (March 2023 forecast) to 87 months (September 2026 forecast). The results in Step 6 are from the corrected run.

**5.4 "Continue this across several periods."**
- **Status:** Done
- **Specifics:**
  - 43 months, March 2023 to September 2026.
  - 774 forecasts in total: 43 months × 2 markets × 9 methods.
- **Why it starts in March 2023:** the inputs need 14 months of history after the 2020–21 gap, and January 2022 plus 14 months is March 2023.
- **Evidence:** `data/model/model_comparison.csv` (602 forecasts), `data/model/tree_models_backtest.csv` (172 forecasts)

**5.5 "This shows how the model would have performed if it had actually been running during those months."**
- **Status:** Done
- **Specifics:**
  - Inputs use the figures as first published, so the test never uses a revision that wasn't known at the time.
  - Each forecast is scored against the Board's newest figure for that month.

---

## Step 6: Evaluate the models

**6.1 "Compare each model using suitable forecasting metrics."**
- **Status:** Done
- **Specifics:** all three of the brief's measures, for every model and market.

**6.2 "Use MAE."**
- **Status:** Done
- **Meaning:** the average size of the miss, in $ millions.
- **Example:** the Strip baseline is off by $43.6m a month on average.

**6.3 "Use RMSE."**
- **Status:** Done
- **Meaning:** like MAE, but big misses count for more.
- **Example:** Strip baseline $58.8m.

**6.4 "Use MAPE."**
- **Status:** Done
- **Meaning:** the average miss as a percentage of the actual figure.
- **Example:** Strip baseline 5.8%.

**6.5 "Also record training time and prediction time."**
- **Status:** Partly
- **Specifics:** recorded as seconds per forecast, with training and prediction together. Baselines 0.000; ARIMA 0.02–0.03; Seasonal ARIMA 0.08–0.13; with inputs 0.21–0.85; Random Forest 0.19; XGBoost 0.16.
- **Gap:** training and prediction time aren't recorded separately.

**6.6 "Create a comparison table."**
- **Status:** Done
- **Specifics:** two months ahead, 43 months:

  | Model | Strip MAE ($m) | Strip RMSE ($m) | Strip MAPE | Reno MAE ($m) | Reno RMSE ($m) | Reno MAPE | Seconds per forecast |
  |---|---|---|---|---|---|---|---|
  | Same month last year | **43.6** | 58.8 | **5.8%** | 4.8 | 6.3 | **7.2%** | 0.000 |
  | Last published | 76.7 | 90.9 | 10.4% | 7.2 | 8.9 | 11.5% | 0.000 |
  | ARIMA | 58.1 | 73.5 | 7.8% | 7.0 | 8.2 | 10.9% | 0.02–0.03 |
  | Seasonal ARIMA | 49.0 | 61.6 | 6.6% | 6.0 | 10.6 | 9.5% | 0.08–0.13 |
  | Seasonal ARIMA + calendar | 46.5 | **58.2** | 6.3% | 5.2 | 6.6 | 8.1% | 0.21–0.57 |
  | Seasonal ARIMA + game mix | 49.9 | 63.9 | 6.7% | **4.7** | **6.0** | **7.2%** | 0.37–0.38 |
  | Seasonal ARIMA + both | 45.7 | 58.4 | 6.1% | 5.0 | 6.4 | 7.8% | 0.66–0.85 |
  | Random Forest | 50.0 | 65.7 | 6.7% | 4.9 | **6.1** | 7.5% | 0.19 |
  | XGBoost | 52.3 | 70.3 | 7.1% | 5.2 | 6.4 | 7.9% | 0.16 |
  | LSTM | not tested | | | | | | |

  *Random Forest and XGBoost: corrected run, 12 Nov 2026 (see 5.3).*
- **Evidence:** `data/model/model_comparison.md`, `data/model/tree_models_backtest.csv`

**6.7 "The student should explain which model should be selected and why."**
- **Status:** Done
- **Specifics:** "same month last year" is selected (D28). It has the lowest average miss on the Strip in % and in $, ties on Reno, has nothing to train or maintain, and anyone can check it.
- **Evidence:** `docs/week4-model-comparison.md`

**6.8 "The decision should not be based only on one metric."**
- **Status:** Partly
- **What the three measures show:**
  - **Strip:** the baseline is best on MAE and MAPE. On RMSE, Seasonal ARIMA + calendar ($58.2m) and + both ($58.4m) are slightly better than the baseline ($58.8m). They have fewer very large misses.
  - **Reno:** Seasonal ARIMA + game mix is slightly better on MAE and RMSE, and equal on MAPE. Random Forest is also slightly better on RMSE ($6.1m against $6.3m), but worse on MAE and MAPE.
  - These differences are small, about 1% of the miss on the Strip.
- **Correction:** `docs/week4-model-comparison.md` says "no model beats it" for the Strip. That's true for MAE and MAPE, but not for RMSE, and the document needs updating.
- **Gap:** record which measure matters most (a product decision, Step 16).

**6.9 "Model complexity, maintenance, prediction speed, and business usefulness should also be considered."**
- **Status:** Partly (this table is new, for your review)
- **Specifics:**

  | Factor | Same month last year | Seasonal ARIMA + inputs | Random Forest / XGBoost |
  |---|---|---|---|
  | Complexity | None: one lookup | Statistical model, retrained each month | Hundreds of trees, 12 inputs |
  | Maintenance | None | Monthly retrain, plus calendar and game-mix data from the 48-page report | Monthly retrain, plus 12 inputs from both reports |
  | Prediction speed | Instant | Under 1 second | Under 0.2 seconds |
  | Explaining it | "Same as this month last year" | Needs statistics to explain | Hard to explain why it gave a number |
  | Business usefulness | Accurate, and easy to trust and check | Slightly fewer big misses on the Strip | No better than the baseline, even with the corrected training |
- **Gap:** this table isn't yet in `docs/week4-model-comparison.md`

---

## Step 7: MLflow experiment tracking

**What this step is for:** one searchable history of every model run (what was trained, on which data, with which settings, how well it did), instead of scattered files.

**Where we are:** done (D46). MLflow 3.18 runs on this computer only, with its usage statistics switched off.
- **Store:** `mlflow/` in the project.
- **Script:** `scripts/mlflow_log.py`.
- **Viewer:** `.venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db --port 5050`.
- **One experiment, 18 runs:** 9 methods × 2 markets, each named like "Reno | SARIMA + game mix".

**7.1 "Use MLflow to track all experiments."**
- **Status:** Done
- **Specifics:** all 18 backtest runs are recorded

**7.2 "For every experiment, record the model name."**
- **Status:** Done
- **Specifics:** run name, plus the `model` and `market` tags

**7.3 "Record the training period."**
- **Status:** Done
- **Specifics:**
  - `training_period`: January 2015 to two months before each forecast, with 2020–21 left out.
  - `test_period`: March 2023 to September 2026.

**7.4 "Record the features used."**
- **Status:** Done
- **Specifics:** `features` parameter, for example "slot share of win (two months back); sports pool share of win (two months back)"

**7.5 "Record the hyperparameters."**
- **Status:** Done
- **Specifics:**
  - ARIMA models: the seasonal term, the version chosen each month, and the final model's version.
  - Random Forest: 300 trees, at least 2 months per leaf.
  - XGBoost: 200 trees, depth 3, learning rate 0.05, 80% sampling.

**7.6 "Record MAE."** · **7.7 "Record RMSE."** · **7.8 "Record MAPE."**
- **Status:** Done
- **Specifics:** `MAE_m`, `RMSE_m` and `MAPE_pct`, plus `bias_m`, `MAPE_last12_pct`, and `monthly_miss_pct` for each of the 43 months, so the error can be charted over time

**7.9 "Record training time."**
- **Status:** Done, with one limit
- **Specifics:** `seconds_per_forecast`. This covers training and prediction together, which is noted on every run.

**7.10 "Record model artifacts."**
- **Status:** Done
- **Specifics:** every run stores its model fitted on all data to September 2026, and its 43 forecasts (`forecasts.csv`). The production rule and Reno V2 are stored as loadable MLflow models.

**7.11 "Record forecast charts."**
- **Status:** Done
- **Specifics:** `forecast_chart.png` on every run: actual against forecast over the 43 months, with the MAPE in the title

**7.12 "The purpose is to have a proper experiment history instead of keeping different versions in separate notebooks."**
- **Status:** Done
- **Specifics:** every run is in one place, comparable side by side, and reproducible from its script

---

## Step 8: Model selection

**8.1 "After comparing the experiments, select the best model."**
- **Status:** Done
- **Specifics:** "same month last year", for the Strip and Reno (D28, approved by you)

**8.2 "The student should document why that model was selected."**
- **Status:** Done
- **Evidence:** `docs/week4-model-comparison.md`, and Steps 6.7 and 6.9 above

**8.3 "For example, one model may have slightly better RMSE but may be much more difficult to maintain."**
- **Status:** Done. This is exactly our case.
- **Specifics:** on the Strip, Seasonal ARIMA + calendar has a slightly better RMSE ($58.2m against the baseline's $58.8m). But it needs retraining every month and extra calendar data, and it's worse on MAE and MAPE. So the baseline was kept.

**8.4 "Another model may have slightly lower accuracy but may be easier to explain and deploy."**
- **Status:** Done
- **Specifics:** the baseline is both the easiest to explain ("the same as this month last year") and the most accurate on average error. Nothing had to be traded off.

**8.5 "The final decision should consider both technical and business factors."**
- **Status:** Partly
- **What exists:** the complexity, maintenance, speed and usefulness table in Step 6.9
- **To do:** add that table to `docs/week4-model-comparison.md`

---

## Step 9: MLflow model registry

**What this step is for:** the official list of model versions, showing which is in production now, which came before, and why it changed.

**Where we are:** done (D46). One registered model per market. Labels (MLflow calls them aliases) show which version is **production** and which is **challenger**. Each version records its decision and reason.

| Registered model | Version | What it is | Label | Forecast for November 2026, loaded from the registry |
|---|---|---|---|---|
| Revenue Forecast Model – LV Strip | 1 | Same month last year | production | $784.3m |
| Revenue Forecast Model – Reno | 1 | Same month last year | challenger | $55.6m |
| Revenue Forecast Model – Reno | 2 | Seasonal ARIMA + game mix | production | $64.4m |

These match the monitoring forecasts exactly, which was the check that the registry works.

**9.1 "Register the selected model in MLflow."**
- **Status:** Done

**9.2 "Create a production model version."**
- **Status:** Done
- **Specifics:** the "production" label on Strip version 1 and Reno version 2

**9.3 "For example: Revenue Forecast Model V1."**
- **Status:** Done
- **Specifics:** V1 = "same month last year", for both markets

**9.4 "Later, if an improved model is trained, create: Revenue Forecast Model V2."**
- **Status:** Done, for Reno
- **Specifics:** Reno V2 = Seasonal ARIMA + game mix, in production from the November 2026 forecast

**9.5 "Document why the new version should replace the old version."**
- **Status:** Done
- **Specifics:** Reno V2's description in the registry records the promotion rule passed three months in a row:
  - last-12-month MAPE 5.6% against 6.8%;
  - full test 7.21% against 7.24%;
  - lower RMSE and bias.

  It also records the Product Owner's approval (D36) and the evidence pack (`docs/week4-reno-switch-evidence-pack.md`).

**9.6 "The student should maintain a clear model history."**
- **Status:** Done
- **Specifics:** versions and labels in the registry, each tagged with its decision (D28, D32, D33, D36, D45), plus the written history in the decision log

---

## Step 10: Champion and Challenger model

**What this step is for:** the Champion is the model in use. A Challenger runs alongside it on the same months. The Challenger takes over only if it keeps winning under a rule agreed in advance.

**10.1 "Use the production model as the Champion model."**
- **Status:** Done
- **Specifics:** Champion = "same month last year" (D28)

**10.2 "Train another model as the Challenger."**
- **Status:** Done (D41)
- **Specifics:**
  - Strip: Seasonal ARIMA + both (calendar and game mix).
  - Reno: Seasonal ARIMA + game mix.
  - When Reno switches (D36), "same month last year" becomes Reno's Challenger.

**10.3 "Both models should make predictions on the same new data."**
- **Status:** Done
- **Specifics:** every monitoring run forecasts with both the Champion and the Challenger, on the same new month (`forecast_log.csv`)

**10.4 "Compare their performance over several periods."**
- **Status:** Partly
- **What exists:** both over all 43 months
- **Year by year** (average monthly miss, MAPE), calculated from the saved forecasts:

  | Period | Strip: Champion | Strip: Seasonal ARIMA + both | Reno: Champion | Reno: Seasonal ARIMA + game mix |
  |---|---|---|---|---|
  | 2023 (Mar–Dec) | **5.6%** | 6.6% | **5.7%** | 6.8% |
  | 2024 | **5.3%** | 6.1% | 9.8% | **9.1%** |
  | 2025 | **6.5%** | 6.6% | **5.2%** | 6.8% |
  | 2026 (Jan–Sep) | 5.6% | **5.1%** | 8.1% | **5.8%** |
  | **Last 12 months** (Oct 2025–Sep 2026) | 5.4% | **4.7%** | 6.8% | **5.6%** |
  | Full test (43 months) | **5.75%** | 6.14% | 7.24% | **7.21%** |
- **What it shows:**
  - Over the last 12 months, the Challengers are ahead in both markets.
  - Over the full test, the Strip Challenger is behind, and Reno's is ahead by just 0.03 points, which is noise.
  - That's exactly the situation the promotion rule has to decide.

**10.5 "The Challenger should only replace the Champion if it consistently performs better according to the agreed evaluation criteria."**
- **Status:** Done
- **Specifics:** monitoring runs the agreed check (D32) every month. Reno's Challenger passed 4 checks in a row. The switch was approved (D36), and Reno V2 is in production from the November 2026 forecast (D45).

**10.6 "The student should define the rules for model promotion."**
- **Status:** Done (D32)
- **The rule, applied to each market separately:** a Challenger is recommended to replace the Champion when all four of these hold at 3 monthly checks in a row:
  1. Its MAPE over the last 12 months is at least 0.5 points lower.
  2. Its MAPE over the whole test is no more than 0.25 points worse.
  3. Its RMSE over the last 12 months is no worse.
  4. Its bias over the last 12 months is no larger.

  A person approves the change.
- **How it was chosen:** five versions were tested month by month. With "better over the last 12 months" alone, the winner would have switched 9 times on the Strip and 8 times on Reno in 32 checks. The margin, the long-term check and the 3-in-a-row requirement stop switching on noise.
- **What it gives on our history:**
  - Strip: never triggers.
  - Reno: triggers in October 2024 and August 2026.
- **Lesson:** after the October 2024 trigger, the Reno Challenger did worse through 2025 (6.8% against 5.2%). So the rule needs a way back.
- **The way back (D33):** the replaced Champion becomes the Challenger, under the same rule.
- **Replayed over the test:**

  | | Strip | Reno |
  |---|---|---|
  | Switches | None | One, October 2024, to Seasonal ARIMA + game mix |
  | Switched back? | — | No. The old model had a lower MAPE in 2025, but its bias and RMSE guards failed |
  | MAPE, Mar 2024–Sep 2026: following the rule | 5.69% | 6.67% |
  | Always the simple model | 5.69% | 6.74% |
  | Always the Challenger | 5.91% | 6.75% |
- **Reno switch:** approved by the Product Owner, effective once monthly monitoring runs (D36). Evidence: `docs/week4-reno-switch-evidence-pack.md`.

---

## Step 11: Model observability

**What this step is for:** once the model is in use, keep checking each month how its forecasts compare with what actually happened, so you notice when it starts getting worse.

**Where we are:** built (D45). `scripts/monitor.py` runs each time the Board publishes a month. It has been replayed over all 43 test months, plus a first live run on September 2026 data. Outputs are in `data/monitoring/`:
- `monthly_status.csv`: one row per market per month.
- `forecast_log.csv`: every forecast made, by which model and version.
- `report_<month>.md`: a readable summary.

**Latest run (data to September 2026):**

| Market | Model in use | Actual | Forecast | Miss | 12-month MAPE | Bias (12 months) | Status |
|---|---|---|---|---|---|---|---|
| LV Strip | Same month last year (V1) | $693.5m | $687.8m | +0.8% | 5.39% | +$14.5m (too low) | Healthy |
| Reno | Same month last year (V1) | $73.0m | $75.7m | −3.7% | 6.76% | +$4.2m (too low) | Healthy |

**11.1 "Once the model is considered deployed, monitor its performance over time."**
- **Status:** Done
- **How:** each run checks the new month's data, scores the forecast made two months earlier, updates the rolling measures and alerts, runs the promotion check, and makes the next forecast.

**11.2 "Track actual revenue."**
- **Status:** Done
- **Specifics:** `actual_m` column in `monthly_status.csv`

**11.3 "Track forecast revenue."**
- **Status:** Done
- **Specifics:** `forecast_m` in `monthly_status.csv`, and every forecast in `forecast_log.csv`. Next forecasts (November 2026): Strip $784.3m (V1), Reno $64.4m (V2).

**11.4 "Track prediction error."**
- **Status:** Done
- **Specifics:** `miss_pct`, the miss for each month, signed so you can see which way it went

**11.5 "Track MAE over time."** · **11.6 "Track MAPE over time."**
- **Status:** Done
- **Specifics:** 12-month MAE, MAPE and RMSE, plus bias (D31), recalculated every month

**11.7 "Track missing input data."**
- **Status:** Done
- **Specifics:** the `data_check` column records each check that fails. A late-release alert fires 7 days after the usual date (D38).

**11.8 "Track model version."**
- **Status:** Done
- **Specifics:** the version for each market is recorded in `data/monitoring/production.json` and stamped on every forecast. The full registry moves to MLflow in Step 9.

**11.9 "Track last retraining date."**
- **Status:** Done
- **Specifics:** in `forecast_log.csv`. The Challengers and Reno V2 were retrained on data to September 2026. "Same month last year" shows "not applicable".

**11.10 "Track model health."**
- **Status:** Done
- **Specifics:** Healthy, Investigate or Data issue, every month (D37, D38)

**11.11 "The purpose is to identify when the production model starts performing worse."**
- **Status:** Done
- **What the replay shows:** monitoring would have flagged:
  - the Strip in 5 months (capacity changes in Dec 2023 and Jan 2024, a slow decline in Aug 2024, a bad patch in Feb–Mar 2025);
  - Reno in 8 months (a slow decline through 2024, a bad patch in Dec 2024–Jan 2025, capacity changes in May 2025 and May 2026, a bad patch in Aug 2026).

---

## Step 12: Data quality monitoring

**What this step is for:** before making a forecast, check the new data is complete and makes sense. If it isn't, don't use it.

**Where we are:** built into monthly monitoring (D38, D45). It was tested on a deliberately broken copy of September 2026: both markets were marked Data issue, the bad month wasn't scored, the Strip kept forecasting, and Reno fell back to "same month last year".

**12.1 "Before generating a forecast, validate the incoming data."**
- **Status:** Done
- **Specifics:** the first step of every monitoring run

**12.2 "Check whether the required month exists."**
- **Status:** Done
- **Specifics:** the month must appear exactly once in the downloads. A late release raises an alert.

**12.3 "Check whether the revenue value is valid."**
- **Status:** Done
- **Specifics:** no zero or negative values. Each county's markets add up to the county, and the counties to the statewide total, within $10. The two readers must agree.

**12.4 "Check whether duplicate records exist."**
- **Status:** Done
- **Specifics:** the month must appear exactly once, and there must be exactly 20 areas

**12.5 "Check whether expected markets are available."**
- **Status:** Done
- **Specifics:** all 20 areas, plus the game-mix data for models that need it

**12.6 "Check whether the data structure has changed."**
- **Status:** Done
- **Specifics:** a changed layout breaks the 20-area and add-up checks, so it's caught. All known layouts are catalogued (`docs/week4-report-catalogue.md`).

**12.7 "The model should not automatically generate a forecast when the input data is incomplete or incorrect."**
- **Status:** Done (D38)
- **Specifics:** a month that fails isn't used, and the market is marked Data issue. "Same month last year" keeps forecasting (it needs only last year's checked figure), labelled. Reno V2 falls back to it. Scoring and alerts pause.

---

## Step 13: Model drift

**What this step is for:** spot when the world has changed enough that the model may no longer fit.
- **Data drift** means the inputs change, such as fewer machines or a closure.
- **Performance drift** means the forecasts get worse.

**Where we are:** built into monthly monitoring (D37, D45).

**13.1 "Monitor whether the behaviour of the incoming data changes compared with the data used to train the model."**
- **Status:** Done
- **Specifics:** capacity alert. Tables or slot machines changed by more than 5% on a year earlier. Fired for the Strip in Dec 2023, Jan 2024 and Feb 2025, and for Reno in May 2025 and May 2026.

**13.2 "Also monitor whether model performance becomes worse over time."**
- **Status:** Done
- **Specifics:**
  - Fast alert: 2 of the last 3 months in the worst 10% of misses.
  - Slow alert: 12-month MAPE more than 1.5 points above normal.

**13.3 "The student should understand the difference between data drift and performance drift."**
- **Status:** Done. Both kinds are monitored separately, as above.

**13.4 "A single unusual month should not automatically trigger retraining."**
- **Status:** Done
- **Specifics:** the fast alert needs 2 bad months in 3, and an alert leads to an investigation, not retraining. Example: Reno's 35.5% miss in January 2024 raised no alert on its own.

**13.5 "The student should define when drift becomes important enough to require investigation."**
- **Status:** Done (D37)
- **The rule, per market:** the status becomes **Investigate** when any alert fires:

  | Alert | Fires when |
  |---|---|
  | Fast | 2 of the last 3 months have a miss in the worst 10% of the model's history (Strip over 12.4%, Reno over 11.1%) |
  | Slow | 12-month MAPE more than 1.5 points above the model's normal (Strip over 7.3%, Reno over 8.7%) |
  | Capacity | Tables or slot machines changed by more than 5% on a year earlier |

- **Shown, not alerted:** bias and hold. They were tested as alerts and were too noisy.
- **Thresholds** come from each model's own test history.

---

## Step 14: Retraining strategy

**What this step is for:** decide, in advance, when a model gets rebuilt.

**What retraining means here:** a model has settings it learns from history, such as how much weight to give recent months, how strong the season is, and how much game mix matters. Retraining means re-learning those settings with the newest data. A model that isn't retrained still uses each new month as an input. "Same month last year" has no settings to learn.

**14.1 "Create a retraining policy."**
- **Status:** Done (D39). Routine retraining runs inside monthly monitoring (D45). Full reviews are scheduled yearly and on alerts.
- **Two layers:**
  - **Routine retraining:** models that learn settings (the Challengers, and Reno V2 once live) re-learn them every month on all data published so far.
  - **Full model review:** re-run the whole comparison with the newest data, try new inputs and markets, and recalculate the alert thresholds. Any change goes through the promotion rule (D32) and the Product Owner (D34).

**14.2 "The student should decide when retraining is required."**
- **Status:** Decided (D39)
- **Routine:** monthly.
- **Full review:** once a year, plus when:
  - a slow alert fires;
  - a capacity alert reflects a real change, such as an opening or closure;
  - or the investigation of a fast alert finds a lasting cause.

**14.3 "For example, retraining may be considered when prediction error remains above the accepted threshold for multiple periods."**
- **Status:** Decided (D37, D39)
- **Specifics:** the slow alert (12-month MAPE more than 1.5 points above normal) is the "error above threshold for multiple periods" trigger. The fast alert (2 of the last 3 months in the worst 10%) leads to an investigation first. A single bad month never triggers anything.

**14.4 "Retraining may also be considered when the data pattern changes significantly."**
- **Status:** Decided (D37, D39)
- **Specifics:** a capacity change of more than 5% in tables or slot machines on a year earlier triggers a review, if it reflects a real change. Example: the Mirage and Tropicana closures in 2024.

**14.5 "The exact rule should be based on project results rather than an arbitrary value."**
- **Status:** Done
- **Evidence:** retraining was tested on the 43 test months (average % error):

  | Model | Monthly | Yearly | Never |
  |---|---|---|---|
  | Strip, Seasonal ARIMA + both | **6.14%** | 6.52% | 7.67% |
  | Reno, Seasonal ARIMA + game mix | 7.21% | 7.18% | **6.99%** |

  - Retraining clearly helps the Strip.
  - For Reno it's near-neutral, and slightly better frozen.
  - Monthly was chosen for both, for simplicity, and because it's the set-up the Reno switch was approved on.
  - The alert thresholds come from the test's own error distribution.

---

## Step 15: Monitoring dashboard

**Status:** Done (D47).
- **Built in:** Streamlit, `dashboard/app.py`. It runs on your computer only.
- **To run it:** `.venv/bin/streamlit run dashboard/app.py --server.port 8504`
- **Checked:** in the browser, for both markets.

| # | The dashboard should show | Status | Where on the page |
|---|---|---|---|
| 15.1 | "Create a dashboard for model monitoring." | Done | One page, with a market picker |
| 15.2 | Actual revenue | Done | "Actual against forecast" chart |
| 15.3 | Forecast revenue | Done | Same chart, plus the next forecast from the production model and the Challenger |
| 15.4 | Forecast error | Done | Monthly miss bars, with bad months in red |
| 15.5 | Historical revenue trends | Done | "Historical revenue, 2015 to now", with the 2020–21 gap shown |
| 15.6 | The current production model | Done | "In production for the next forecast" |
| 15.7 | The model version | Done | "Production version" (V1 or V2) |
| 15.8 | The latest evaluation metrics | Done | 12-month MAPE, MAE, RMSE and bias |
| 15.9 | Drift status | Done | Status this month, months flagged in the last 12, and the flagged-months table with each alert |
| 15.10 | Last retraining date | Done | "Last retrained" ("n/a" for the rule) |
| 15.11 | Healthy or requires investigation | Done | Coloured status badge next to the market name |

---

## Step 16: Product decisions

**What this step is for:** write down the decisions that make this a product, not just a model: what's in use, how it's judged, and who decides when it changes.

**16.1 "Document the important product decisions."**
- **Status:** Done, for the decisions made so far
- **Evidence:** `docs/week4-decision-log.md`, D1 to D30: what was decided, why, and who decided

**16.2 "Explain which model should go into production."**
- **Status:** Done
- **Specifics:** "same month last year", for both markets (D28). It's the most accurate on average error over 43 months, has nothing to maintain, and can be checked by anyone.

**16.3 "Explain which evaluation metric matters most."**
- **Status:** Done (D31)
- **Decision:**
  - **MAPE** (average % miss) is the headline measure. It decides promotion, drift and whether an error is acceptable.
  - **RMSE** is a guard: a new model must not make big misses worse.
  - **Bias** (the average miss with its sign) is tracked.
  - **MAE** is reported in dollars for finance.
- **Why:**
  - Four markets of very different size need one comparable view.
  - One big miss hurts more than several small ones.
  - Reno's forecast was too low in 28 of 43 months, which only bias shows.

**16.4 "Explain when a model should be retrained."**
- **Status:** Done (D39)
- **Specifics:** routine retraining every month. A full review once a year, and on a slow alert, a real capacity change, or a fast alert with a lasting cause.

**16.5 "Explain when a Challenger should replace the Champion."**
- **Status:** Done (D32)
- **Specifics:** the rule in Step 10.6, with the way back (D33). The Reno switch awaits approval.

**16.6 "Explain what should happen when incoming data is incomplete."**
- **Status:** Done (D38)
- **Specifics:** the rule in Step 12.7. A bad month is never used. Forecasts continue on the current model, labelled. More complex models fall back. The analyst is alerted.

**16.7 "Explain what should happen if a new model performs worse than the existing model."**
- **Status:** Done (D40)
- **Specifics:**
  - A worse model isn't promoted. It keeps running as a Challenger if it's close, or is dropped at the yearly review.
  - If a promoted model later becomes worse, the way back (D33) returns the old model through the same rule. Operations can also fall back to "same month last year" at once in an emergency (D34).
- **Example:** Random Forest and XGBoost were tested, came out worse, and nothing changed.

**16.8 "Explain who should approve replacing the production model."**
- **Status:** Done (D34)
- **Decision:** the **Product Owner** approves, after the analyst presents an evidence pack:
  - the four rule checks,
  - what changes to run the new model,
  - the history,
  - the way back.

  Finance is consulted. The person who proposes a change never approves it alone.
- **Emergency fallback:** if the production model or its data fails, operations may switch a market back to "same month last year" straight away, with a review afterwards. The simple model needs only last year's figure, so it can always produce a forecast.

---

## Step 17: Risks

**17.1 "Document the main risks."**
- **Status:** Partly
- **What exists:** the limits section of `docs/week4-model-comparison.md`
- **To do:** a short risk register, using the table below

| # | Risk (the brief's words) | Seen in our project? | What protects against it | Status of protection |
|---|---|---|---|---|
| 17.2 | "The model may perform well during training but poorly on future data." | Yes. The tree models fitted their training months well but didn't beat the baseline on unseen months | Every model is judged only on months it never saw (43-month backtest) | Done. Ongoing monitoring not started |
| 17.3 | "Historical patterns may change." | Yes: growth slowed to about 1% a year, Strip machines fell 20%, and the COVID years were very different | 2020–21 left out (D23). Drift checks (Step 13) | Partly |
| 17.4 | "Seasonal behaviour may affect performance." | Yes: December is about 10% above an average month, and February and August are below | The production model is built on the seasons. Calendar inputs were tested | Done |
| 17.5 | "Missing monthly data may produce incorrect forecasts." | Yes: January 2025's table is a picture, the June and July 2025 reports are partly unreadable, and the data always arrives four weeks late | Two-month-ahead forecasts (D19). Data checks (Step 12). A rule for what happens when data is bad | Partly. The rule isn't decided |
| 17.6 | "A new model may perform better on one period but worse overall." | Yes, right now: the Challengers beat the Champion over the last 12 months but not over the full test | A promotion rule that needs both | Proposed |
| 17.7 | "The business may trust forecasts without reviewing uncertainty." | Yes: forecasts are single numbers today | Show a range with every forecast. For the Strip, a typical miss is 4.1% and a bad month is over 12.4% | Not started |
| 17.8 | "The model may remain in production even after its performance has degraded." | Not yet observed | Monthly monitoring, a health status, and review triggers (Steps 11, 13, 14) | Not started |

---

## Step 18: Final deliverables

| # | The final project should contain | Status | Where / what's missing |
|---|---|---|---|
| 18.1 | A clean historical casino revenue dataset | Done | `data/clean/monthly_win.csv` (2,340 rows), plus game types and capacity. Gap: source and derived columns aren't split (1.4) |
| 18.2 | Exploratory analysis | Done | `docs/week4-exploratory-analysis.md`: 2015 onward, four markets, capacity and hold, four charts (D48) |
| 18.3 | A baseline forecasting model | Done | Two baselines (Step 3). Gap: moving-average baseline |
| 18.4 | At least two additional forecasting models | Done | Seven (Step 4) |
| 18.5 | Time based backtesting | Done | 43 months, 774 forecasts (Step 5) |
| 18.6 | Model evaluation results | Done | Step 6, `data/model/model_comparison.md` |
| 18.7 | MLflow experiment tracking | Done | Step 7 |
| 18.8 | A registered production model | Done | Step 9 |
| 18.9 | Champion and Challenger comparison | Done | Monthly in monitoring (Step 10). Reno V2 promoted |
| 18.10 | Data quality monitoring | Done | Step 12 |
| 18.11 | Model drift monitoring | Done | Step 13 |
| 18.12 | A retraining strategy | Done | Step 14. Policy decided and tested (D39) |
| 18.13 | A model monitoring dashboard | Done | Step 15 |
| 18.14 | A GitHub repository | Done | https://github.com/tezla-timemachine/casino-revenue-forecasting (public, D49) |
| 18.15 | A short document explaining why the final production model was selected | Done | `docs/week4-model-comparison.md`, corrected today. Still to add: the factor table from 6.9 |
