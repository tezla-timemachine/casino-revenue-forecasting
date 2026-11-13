# Feature checks: data/features/features_strip_reno.csv

Rows: 86 (43 months x 2 markets), 2023-03 to 2026-09.
Starts in March 2023: the year-on-year feature needs history back to January 2022, the first month we hold. Forecast horizon: two months ahead (decision D19), so each feature uses months up to two months before the target.

- Missing values: none
- Same-month-last-year MAPE rebuilt from the features: 6.49% over 86 rows per market. Compare with data/model/baseline_backtest.csv over the same months (March 2023 onwards).
  - LV Strip: 5.75%
  - Reno: 7.24%
- Leakage: every feature uses months at least two before the target, the newest figures published by then. Checked by construction in the script.
