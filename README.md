# Casino revenue forecasting and model monitoring

Week 4 project: a full machine-learning lifecycle for forecasting monthly casino gaming win in Nevada, using the Nevada Gaming Control Board's official reports. It covers data preparation, model comparison, backtesting, MLflow tracking and registry, Champion/Challenger, monitoring, drift, retraining and a dashboard.

**Start here:** [`docs/week4-brief-traceability.md`](docs/week4-brief-traceability.md) goes through every point of the brief: what was done, how, and where the evidence is.

## Results in brief

| | LV Strip | Reno |
|---|---|---|
| Production model | Same month last year (V1) | Seasonal ARIMA + game mix (V2, from the Nov 2026 forecast) |
| Average error, 43-month backtest (MAPE) | 5.8% | 7.2% |
| Status (data to Sep 2026) | Healthy | Healthy |
| Forecast for Nov 2026 | $784.3m | $64.4m |

Forecasts are two months ahead, because the Board publishes about four weeks after each month ends.

## Documents

| Document | What it covers |
|---|---|
| [The brief, with what we did](docs/week4-brief-what-we-did.docx) ([PDF](docs/week4-brief-what-we-did.pdf)) | The original brief, unchanged, with a short 'What we did' box under every point. The easiest way in |
| [Brief, bullet by bullet](docs/week4-brief-traceability.md) | Every point of the brief, with its status and evidence |
| [Decision log](docs/week4-decision-log.md) | Every decision (D1 to D54): what, why, who |
| [Model comparison](docs/week4-model-comparison.md) | Why the production model was chosen |
| [Exploratory analysis](docs/week4-exploratory-analysis.md) | Trends, seasons, capacity and hold, 2015 to 2026 |
| [Report catalogue](docs/week4-report-catalogue.md) and [fields](docs/week4-report-fields.md) | The Board's reports, their layouts and fields |
| [Revision review](docs/week4-revision-review.md) | How the Board's figure revisions were checked |
| [Reno switch evidence pack](docs/week4-reno-switch-evidence-pack.md) | The case for promoting Reno V2, and the approval |

## Set up and run

```bash
python3.10 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 scripts/fetch_arr.py --download                      # monthly releases, 2022 onward
python3 scripts/fetch_arr.py --start 2015-01 --end 2019-12 --download
python3 scripts/fetch_board_reports.py --download            # Monthly Revenue Reports, 2022 onward
python3 scripts/fetch_board_reports.py --start 2015-01 --end 2019-12 --download
.venv/bin/python scripts/monitor.py                          # monthly monitoring run
.venv/bin/python scripts/mlflow_log.py                       # rebuild the MLflow store (mlflow/)
.venv/bin/streamlit run dashboard/app.py --server.port 8504   # monitoring dashboard
```

The clean data, backtest results and monitoring outputs are already in `data/`, so the dashboard runs without downloading anything.

## Monthly routine (run by hand, D54)

**When:** the first working day of each month. The Board publishes each month's figures by the end of the following month, so on 1 December the October figures should be out. If they aren't, run again on the 8th: monitoring raises the late-data alert 7 days after the due date (D38).

```bash
python3 scripts/fetch_arr.py --download                # 1. download the new month's reports
python3 scripts/fetch_board_reports.py --download
.venv/bin/python scripts/extract_reports.py            # 2. read them two ways and build the clean tables
.venv/bin/python scripts/build_table.py
.venv/bin/python scripts/build_game_types.py
.venv/bin/python scripts/extract_capacity_hold.py
python3 scripts/build_calendar.py                      # 3. features
.venv/bin/python scripts/build_features.py
.venv/bin/python scripts/compare_models.py             # 4. score the models on the new month
.venv/bin/python scripts/bottom_up.py
.venv/bin/python scripts/monitor.py                    # 5. checks, alerts, promotion check, next forecast and range
.venv/bin/streamlit run dashboard/app.py --server.port 8504   # 6. review the dashboard
```

**Then:** read `data/monitoring/report_<month>.md`. If a market shows **Investigate** or **Data issue**, the analyst explains the cause within the month (D37, D38). A switch recommendation goes to the Product Owner (D34).

Not yet run on a new month: the first real run is when the October 2026 figures are published (due by 30 November 2026).

## Layout

| Folder | Contents |
|---|---|
| `scripts/` | Downloading, reading the reports two ways, building tables and features, baselines and models (including bottom-up), 80% forecast ranges, monitoring, MLflow, charts |
| `data/clean/` | Clean monthly win (20 areas × 117 months), win by game type, capacity and hold |
| `data/features/` | Forecasting features and the calendar |
| `data/model/` | Backtest results for every model |
| `data/monitoring/` | Monthly status, forecast log, production versions, thresholds, reports |
| `dashboard/` | Streamlit monitoring dashboard |
| `docs/` | Documents (Markdown and Word) and charts |

Data source: Nevada Gaming Control Board, public monthly reports. 2020 and 2021 are left out because of the COVID closures.
