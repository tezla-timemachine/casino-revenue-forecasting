# Risk register: casino revenue forecasting (Step 17)

**Status: approved by the Delivery Lead, 13 Nov 2026 (D52).** Reviewed at the yearly model review (D39), or when a new risk appears.

**How to read it**
- **Likelihood:** how likely the risk is to hit in a normal year.
- **Impact:** how much harm it does if it hits.
- **Residual:** what's left after the protections in place today.
- **Owners** are the roles from D34:
  - *Analyst* runs monitoring and investigates;
  - *Product Owner* approves model changes;
  - *Operations* can fall back in an emergency;
  - *Delivery Lead* owns the project.

## Summary

| # | Risk | Likelihood | Impact | Residual | Owner |
|---|---|---|---|---|---|
| R1 | Good in training, poor on future data | Medium | High | **Low** | Analyst |
| R2 | Historical patterns change | High | High | **Medium** | Analyst |
| R3 | Seasonal behaviour affects performance | High | Medium | **Low** | Analyst |
| R4 | Missing or bad monthly data | Medium | High | **Low** | Analyst |
| R5 | Better on one period, worse overall | High | Medium | **Low** | Product Owner |
| R6 | Business trusts forecasts without seeing the uncertainty | High | High | **Low** (was High; D53) | Delivery Lead |
| R7 | Model stays in production after it degrades | Medium | High | **Low** | Analyst |
| R8 | Baccarat luck swings the Strip | High | High | **Medium** | Analyst |
| R9 | Forecasts lean too low | High | Medium | **Medium** | Analyst |
| R10 | The Board changes its report layout | Medium | High | **Low** | Analyst |
| R11 | Published figures are revised later | Medium | Low | **Low** | Analyst |
| R12 | Runs on one computer, started by hand | Medium | Medium | **Medium** (kept manual, D54) | Delivery Lead |

R1 to R7 are the brief's risks (17.2 to 17.8). R8 to R12 are extra risks we met in this project.

**R6, the biggest risk at approval, is now reduced:** every forecast has an 80% range (D53). The open risks are the four rated Medium.

## Details

### R1. "The model may perform well during training but poorly on future data." (17.2)
- **Seen here:** yes.
  - Random Forest and XGBoost learned their training months but lost to the baseline on unseen months: Strip 6.7% and 7.1% against 5.75%.
  - A bug that froze the trees' training window was caught and fixed.
- **Protection:**
  - Every model is judged only on months it never saw: a 43-month backtest, two months ahead, with the figures as first published (D19, D23).
  - The simplest model won and is in production (D28).
- **Next:** none. Monitoring (R7) catches any later decline.

### R2. "Historical patterns may change." (17.3)
- **Seen here:** yes.
  - COVID: 2020–21 were left out (D23).
  - Growth stalled after 2023.
  - Strip slot machines fell 20% (44,370 → 35,466) while win per machine doubled.
  - The December peak strengthened: 1.08 → 1.18 times an average month.
- **Protection:**
  - Drift alerts (D37): slow (12-month MAPE more than 1.5 points above normal) and capacity (tables or slots ±5% on a year earlier).
  - Monthly retraining, plus yearly and alert-triggered reviews (D39).
  - The replay raised the slow alert on the Strip in August 2024 and on Reno four times in 2024.
- **Why still Medium:** the alerts show that something changed, not why. An analyst has to explain each one (D37).
- **Next:** the yearly review re-tests capacity and hold as model inputs.

### R3. "Seasonal behaviour may affect performance." (17.4)
- **Seen here:** yes.
  - December is the Strip's peak, and February and August are low.
  - The seasonal pattern itself moved (see R2).
- **Protection:**
  - Production is "same month last year", which carries the season by design.
  - Seasonal ARIMA models the season.
  - Calendar inputs (days, weekend nights, holidays) were tested.
- **Next:** none.

### R4. "Missing monthly data may produce incorrect forecasts." (17.5)
- **Seen here:** yes.
  - January 2025's table is a picture; it was read by OCR and passed every check.
  - Two links were labelled January 2025 (D7).
  - The June and July 2025 game-mix pages were partly unreadable.
  - Data always arrives about four weeks after the month ends.
- **Protection:**
  - Forecasts are two months ahead, so they never need data that isn't out yet (D19).
  - Bad-data rule (D38): every check must pass before a month is used, otherwise status **Data issue**.
  - Markets that depend on the game mix fall back to "same month last year" (D34).
  - A late release raises an alert after 7 days.
  - Tested on a deliberately broken copy of September 2026.
- **Next:** none.

### R5. "A new model may perform better on one period but worse overall." (17.6)
- **Seen here:** yes.
  - Reno's Challenger met a simple rule in October 2024, then did worse through 2025 (6.8% against 5.2%).
  - A last-12-months-only rule would have switched models 8 or 9 times.
- **Protection:**
  - The promotion rule (D32) needs:
    - a 0.5-point lead over 12 months;
    - no more than 0.25 points worse over the full test;
    - no worse RMSE or bias;
    - all of these at 3 checks in a row.
  - The way back (D33) and Product Owner approval (D34).
  - With two Strip Challengers, the lower 12-month MAPE breaks a tie (D51).
- **Next:** none.

### R6. "The business may trust forecasts without reviewing uncertainty." (17.7)
- **Seen here:** yes. Every forecast is a single number, for example Strip November 2026: $784.3m.
- **How big the uncertainty is:**
  - Strip:
    - a typical miss is 5.75%, about $43m;
    - 1 month in 10 misses by more than 12.4%.
  - Reno: the current model (Seasonal ARIMA + game mix) misses 7.2% on average, and more than 13.8% in 1 month in 10.
- **Protection (D53):**
  - Every forecast now has an 80% range, built from the model's own past misses. Strip November 2026: $784.3m, **range $724m to $893m**.
  - Shown in the monthly report, the forecast log and the dashboard (next to each forecast, and as a band on the chart).
  - Monitoring counts how often the actual lands inside. 7 or fewer of the last 12 raises the range alert.
  - Tested: Strip ranges held in 86% of the 43 test months, Reno's in 87% (target 80%).
- **Why Low now:** the uncertainty sits next to every number. What's left is a reader ignoring it.
- **Next:** none.

### R7. "The model may remain in production even after its performance has degraded." (17.8)
- **Seen here:** not on the production models so far.
  - The replay flagged the Strip in 5 of 43 months and Reno in 8, each time recovering or being explained.
- **Protection:**
  - Monthly monitoring with a health status (D45).
  - Fast and slow alerts (D37).
  - The way back (D33).
  - The emergency fallback to "same month last year" (D34).
  - The yearly review (D39).
  - Thresholds are set per model, so Reno V2 is judged against its own normal.
- **Next:** none. Depends on monitoring actually being run each month (R12).

### R8. Baccarat luck swings the Strip (extra)
- **Seen here:** yes.
  - Strip forecast misses follow baccarat hold (correlation 0.75, D48).
  - Baccarat is played in large amounts by a few players, so the share the casino keeps swings from month to month. That luck can't be known in advance.
- **Protection:**
  - The bottom-up Challenger takes last year's baccarat luck out of the forecast (D50, D51): 5.28% against 5.75% on the backtest.
  - It's held back by R9.
- **Why still Medium:** no forecast can know the luck to come. The range (R6) should be wider on the Strip for this reason.
- **Next:** the R9 fix for bottom-up. The Strip's range (D53) is already wide for this reason: about $170m.

### R9. Forecasts lean too low (extra)
- **Seen here:** yes.
  - Reno's forecasts were too low in 28 of 43 months (D31).
  - The Strip's 12-month bias is +$14.5m.
  - Bottom-up leans lower still (+$19.0m), which blocks its promotion.
- **Protection:**
  - Bias is tracked every month (D31).
  - It's a guard in the promotion rule (D32).
  - It's reviewed quarterly on the dashboard (D37).
- **Why still Medium:** "same month last year" can't see growth, so it runs low whenever revenue grows.
- **Next:** test a growth adjustment, for example last year × the recent year-on-year change.

### R10. The Board changes its report layout (extra)
- **Seen here:** yes.
  - The old layout (before July 2015) differs from the new one.
  - The June/July 2025 detail page has no "Slot Machines" heading.
- **Protection:**
  - Two independent readers must agree.
  - Totals must add up.
  - The month is refused if either check fails (D38).
- **Next:** none. A new layout means a reader fix, during which the fallback runs.

### R11. Published figures are revised later (extra)
- **Seen here:** yes. 10 figures changed by more than 1% a year later; all were real Board revisions, mostly small areas.
- **Protection:**
  - Models use each month's figure as first published (no hindsight).
  - Scoring uses the newest figure (D9).
- **Next:** none.

### R12. Runs on one computer, started by hand (extra)
- **Seen here:** by design.
  - The dashboard and monitoring run on the Delivery Lead's computer (D44).
  - `scripts/monitor.py` is run by hand when the Board publishes.
- **Protection:**
  - Code, data and documents are on GitHub (D49).
  - The README rebuilds everything.
  - The late-data alert (D38) shows only when monitoring is run.
  - **Kept manual by choice (D54)**, with a written monthly routine in the README: run on the first working day of each month, again on the 8th if the figures are late.
- **Why Medium:** if nobody runs it, nothing alerts. R7's protection depends on this.
- **Next:** none for now. Revisit at the yearly review (D39): an automatic schedule on this computer, or hosting (needs approval, D44).

## Open actions

| Priority | Action | Risk |
|---|---|---|
| ~~1~~ | ~~Show a range with every forecast~~: **done (D53)** | R6, R8 |
| ~~2~~ | ~~Schedule the monthly monitoring run~~: **kept manual, with a written routine (D54)** | R12, R7 |
| 3 | Test a growth adjustment for bias | R9, R8 |
| 4 | Yearly review: test capacity and hold as inputs | R2 |
