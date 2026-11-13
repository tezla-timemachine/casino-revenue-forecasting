# Model comparison, two months ahead, 2023-03 to 2026-09 (43 months)

Training history: 2015 onward, with 2020 and 2021 excluded (D23).

| Market | Model | MAE ($m) | RMSE ($m) | MAPE | Seconds per forecast |
|---|---|---|---|---|---|
| LV Strip | baseline last published | 76.68 | 90.92 | 10.4% | 0.000 |
| LV Strip | baseline same month last year | 43.55 | 58.76 | 5.8% | 0.000 |
| LV Strip | ARIMA | 58.06 | 73.51 | 7.8% | 0.034 |
| LV Strip | SARIMA | 48.98 | 61.62 | 6.6% | 0.126 |
| LV Strip | SARIMA + calendar | 46.47 | 58.18 | 6.3% | 0.572 |
| LV Strip | SARIMA + game mix | 49.85 | 63.87 | 6.7% | 0.370 |
| LV Strip | SARIMA + both | 45.73 | 58.35 | 6.1% | 0.845 |
| Reno | baseline last published | 7.21 | 8.86 | 11.5% | 0.000 |
| Reno | baseline same month last year | 4.79 | 6.25 | 7.2% | 0.000 |
| Reno | ARIMA | 6.96 | 8.17 | 10.9% | 0.020 |
| Reno | SARIMA | 6.00 | 10.62 | 9.5% | 0.075 |
| Reno | SARIMA + calendar | 5.24 | 6.55 | 8.1% | 0.214 |
| Reno | SARIMA + game mix | 4.69 | 5.99 | 7.2% | 0.382 |
| Reno | SARIMA + both | 5.04 | 6.42 | 7.8% | 0.663 |
