# Evidence pack: switching Reno's production forecast

**For:** Product Owner (approver, D34) · **Consulted:** Finance / planning lead · **Prepared by:** Analyst · **Date:** 12 November 2026 · **Data to:** September 2026

## 1. The decision asked for

Should Reno's production forecast change from **"same month last year"** (the current Champion) to **Seasonal ARIMA + game mix** (the Challenger)?

The LV Strip isn't affected. Its Champion stays.

## 2. The rule's result

The promotion rule (D32) recommends a switch when all four checks hold at 3 monthly checks in a row. Reno's Challenger has passed every check from June to September 2026:

| Monthly check (data to) | 1. MAPE, last 12 months: Champion vs Challenger (needs ≥ 0.5 points better) | 2. MAPE, whole test (needs ≤ 0.25 points worse) | 3. RMSE, last 12 months (needs no worse) | 4. Bias, last 12 months (needs no larger) | Result |
|---|---|---|---|---|---|
| June 2026 | 6.80% vs 6.25% (0.55 better) | 7.32% vs 7.31% | $6.0m vs $5.7m | +$4.6m vs +$3.3m | Pass |
| July 2026 | 6.13% vs 5.27% (0.86 better) | 7.17% vs 7.20% (0.03 worse) | $5.6m vs $4.8m | +$4.1m vs +$2.5m | Pass |
| August 2026 | 6.87% vs 6.00% (0.87 better) | 7.32% vs 7.30% | $6.4m vs $5.4m | +$4.8m vs +$3.1m | Pass: **rule met (3 in a row)** |
| September 2026 | 6.76% vs 5.59% (1.17 better) | 7.24% vs 7.21% | $6.3m vs $5.2m | +$4.2m vs +$2.4m | Pass |

## 3. What changes for the next forecast

The next forecast is for **November 2026**, made with data to September 2026:

| | Forecast |
|---|---|
| Champion (November 2025's figure) | **$55.6m** |
| Challenger (Seasonal ARIMA + game mix) | **$64.4m** |
| Difference | +$8.8m (+16%) |

**Context for judging these:**
- Reno's past Novembers were $44.5m to $58.0m (2015 to 2025), with the highest in 2023.
- But Reno has run well above last year through 2026. From April to August 2026, actual win was $70.5m to $81.6m a month, and the Champion's forecasts were too low by $7m to $14m in most of those months.
- The Challenger is therefore forecasting that 2026's higher level continues. The Champion assumes November will look like last November.

## 4. Recent track record

| Month | Actual | Champion | Challenger |
|---|---|---|---|
| April 2026 | $72.3m | $64.7m | $66.2m |
| May 2026 | $70.5m | $63.5m | $65.7m |
| June 2026 | $81.6m | $67.8m | $70.4m |
| July 2026 | $76.9m | $76.1m | $74.9m |
| August 2026 | $79.4m | $68.7m | $70.2m |
| September 2026 | $73.0m | $75.7m | $75.5m |

**Over the last 12 months:**
- The Challenger was closer in **8 of 12** months.
- Both forecasts were usually too low: the Champion in 10 of 12 months, the Challenger in 9.
- The worst single month was June 2026 for both: the Champion missed by 16.9%, the Challenger by 13.8%.

## 5. What changes to run it

| | Champion (now) | Challenger |
|---|---|---|
| Data needed each month | The monthly release only | The monthly release **and** the 48-page Monthly Revenue Report, for the slot and sports-betting shares |
| Work each month | One lookup | Refit the model (under a second) |
| Explaining a forecast | "Same as last year" | A statistical model using recent trend, season and game mix |
| If its data is missing | Can't fail: it needs only last year's figure | Falls back to the Champion (D34) |

**Not yet in place:**
- Monthly monitoring (Step 11).
- The model registry (Step 9), which would record this as Reno Revenue Forecast Model V2.

## 6. Risks and history

- **The rule has triggered before.** It would also have switched Reno in October 2024, and the Challenger then had a weaker 2025 (6.8% against 5.2%). The way back (D33) and the emergency fallback (D34) limit the damage if this happens again.
- **Both models under-forecast Reno.** The switch reduces that bias but doesn't remove it.
- **A more complex model is being approved before monitoring exists.** Without monitoring, a slide back wouldn't be spotted quickly.

## 7. Options for the Product Owner

| Option | Effect |
|---|---|
| **A. Approve now** | Reno uses the Challenger from the November 2026 forecast |
| **B. Approve, effective once monthly monitoring is running** (analyst's recommendation) | Same switch, but only once the rule and the way back are checked automatically each month. The Champion stays until then |
| C. Defer three months | Re-check with October to December data |
| D. Reject | Reno stays with the Champion. The Challenger keeps running alongside |

**Analyst's recommendation: B.** The evidence meets the agreed rule, and the Challenger has been closer in 8 of the last 12 months. But approving a more complex model is only safe once monitoring can spot a decline and trigger the way back.

## 8. Decision

| Product Owner's decision | Date | Notes |
|---|---|---|
| **B. Approved, effective once monthly monitoring is running** | 12 November 2026 | Reno stays on "same month last year" until monitoring (Step 11) checks the rule and the way back each month. Then it switches to Seasonal ARIMA + game mix, recorded as Reno V2 |
