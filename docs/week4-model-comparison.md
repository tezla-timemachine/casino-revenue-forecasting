# Model comparison: monthly casino win forecasts for the LV Strip and Reno

Two months ahead, tested on March 2023 to September 2026 (43 months). Source tables: `data/model/model_comparison.md` (statistical models) and `data/model/tree_models_backtest.csv` (tree models).

## 1. The question

The business wants to know what revenue to expect next month, and whether a forecasting model is worth using over a simple rule. The Board publishes each month's figures about four weeks after the month ends, so each forecast uses only figures available two months before the month it predicts.

## 2. How the test was run

- **Data:** the Board's monthly revenue release (ARR) for each market, January 2015 to September 2026, using first-published figures for inputs and the newest figure for the result (decision D9).
- **2020 and 2021 are left out of training.** Casinos were closed for much of 2020, and the months that followed do not behave like normal trading (decision D23).
- **No peeking:** every model is trained on, and every input is taken from, months published before the month being forecast.
- **Same test for every model:** 43 months, one forecast per month, scored against the newest figure.

## 3. Results

Average error (MAPE) and average miss in $ millions (MAE). Lower is better.

| Model | LV Strip MAPE | LV Strip MAE | Reno MAPE | Reno MAE |
|---|---|---|---|---|
| **Same month last year (baseline)** | **5.8%** | **43.6** | **7.2%** | 4.8 |
| Seasonal ARIMA + calendar + game mix | 6.1% | 45.7 | 7.8% | 5.0 |
| Seasonal ARIMA + calendar | 6.3% | 46.5 | 8.1% | 5.2 |
| Random Forest | 6.7% | 50.0 | 7.5% | 4.9 |
| XGBoost | 7.1% | 52.3 | 7.9% | 5.2 |
| Seasonal ARIMA | 6.6% | 49.0 | 9.5% | 6.0 |
| Seasonal ARIMA + game mix | 6.7% | 49.9 | **7.2%** | **4.7** |
| ARIMA (no seasonal term) | 7.8% | 58.1 | 10.9% | 7.0 |
| Last published figure (no model) | 10.4% | 76.7 | 11.5% | 7.2 |

## 4. What the results mean

1. **The simple baseline is the strongest model for the LV Strip on average error.** No model beats it on MAPE or MAE, and the closest is 0.3 points behind. On RMSE, which weighs big misses more, Seasonal ARIMA + calendar ($58.2m) and + both ($58.4m) are slightly better than the baseline ($58.8m).
2. **Reno is a tie.** Seasonal ARIMA with game mix matches the baseline's 7.2% average error and has a slightly smaller typical miss (4.7 against 4.8). Over 43 months, that difference is within normal variation, so it is not a clear win.
3. **Seasonality is the main signal.** Simply repeating last year's month captures most of it. The "last published figure" method, which ignores seasonality, is the worst.
4. **Extra inputs help only a little.** Calendar and game-mix inputs narrowed the gap but did not overtake the baseline.
5. **Tree models do not beat the baseline.** After correcting their training so it grows each month (46 to 87 months), Random Forest and XGBoost are still behind on MAPE for both markets. Random Forest is slightly better on Reno RMSE only.

## 4b. Later test: bottom-up, taking baccarat luck out (D50)

Forecast slots, baccarat and other tables separately. For baccarat, use last year's amount bet times a normal hold (the 24-month average), instead of last year's luck.

| LV Strip | MAPE | MAE ($m) | RMSE ($m) | Bias ($m) | MAPE, last 12 months |
|---|---|---|---|---|---|
| Production (same month last year) | 5.75% | 43.5 | 58.8 | +10.3 | 5.39% |
| **Bottom-up, baccarat luck out** | **5.28%** | **40.2** | **54.6** | +14.5 | **4.26%** |

- **It's the first method to beat the Strip production model on all three measures.**
- **It leans further too low,** so the promotion rule's bias guard blocks it now (July to September 2026). It would have triggered in April 2025 and June 2026.
- **Reno: no gain.** Tables are only a fifth of Reno's win.
- **Now the Strip's second Challenger (D51),** alongside Seasonal ARIMA + both. Recorded in MLflow.

## 5. Recommendation

For now, use **"same month last year" as the production forecast** for both markets. It is the most accurate of the models tested, the simplest to explain, and the cheapest to run.

Replace it only when a challenger model beats it on the same test over a longer period. Suggested rule, for the Delivery Lead to approve: a challenger must have a lower average error on both markets over the most recent 12 months, and on the full test.

## 6. Limits and what is not yet done

- The test covers 43 months, and the Strip and Reno differences between models are small. A longer test would give firmer answers.
- The last 12 months of figures are the Board's latest and can still be revised, so the most recent results may move slightly.
- Not yet done (from the brief): experiment tracking in MLflow, the model registry, champion and challenger tracking, drift monitoring, the retraining policy, the monitoring dashboard and the final GitHub repository.
