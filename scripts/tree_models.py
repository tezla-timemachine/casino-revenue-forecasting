"""Random Forest and XGBoost on the same two-months-ahead test window as compare_models.py (D19, D23, D26).

Each test month is forecast by a model trained only on earlier months, with that month's inputs and target
taken as they were known at the time (first-published figures).

Target: the log of this month's win relative to the same month last year. The forecast is last year's
figure scaled back by the predicted ratio. This keeps the level of the forecast tied to the market's size
(trees cannot extrapolate beyond the values they have seen).

Inputs (all known two months ahead, as in the feature table): last published win, same month last year,
3- and 12-month averages, year-on-year and month-on-month change, slot and sports-pool shares, month of year,
and the calendar for the month forecast. A training row is used only if none of its inputs fall in 2020 or 2021.

    .venv/bin/python scripts/tree_models.py

Writes data/model/tree_models_backtest.csv and prints the metrics. Needs scikit-learn and xgboost (in .venv).
"""
from __future__ import annotations

import csv
import math
import time
import warnings
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
FEATURES = ROOT / "data" / "features"
MODEL = ROOT / "data" / "model"
MARKETS = ["LV Strip", "Reno"]
HORIZON = 2
SCALE = 1e6
TEST_START = "2023-03"
EXCLUDED = {f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)}


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def main() -> None:
    win = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) / SCALE for r in win}
    latest = {(r["month"], r["area"]): float(r["gaming_win"]) / SCALE for r in win}
    games = {(r["month"], r["area"], r["game"]): float(r["win_usd"]) for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv"))}
    cal = {r["month"]: r for r in csv.DictReader(open(FEATURES / "calendar.csv"))}
    months = sorted({r["month"] for r in win})

    def inputs(t, market):
        """Feature vector for month t, using only months up to two months before t. None if unavailable."""
        last = shift(t, -HORIZON)
        window = [shift(t, -n) for n in range(HORIZON, 15)]  # the 13 months the inputs can touch
        if any(m in EXCLUDED or (m, market) not in first for m in window):
            return None
        total = games.get((last, market, "Total gaming"))
        if not total:
            return None
        lag = lambda n: first[(shift(t, -n), market)]
        c = cal[t]
        return [
            lag(HORIZON),                                              # last published
            lag(12),                                                  # same month last year
            sum(lag(n) for n in range(HORIZON, HORIZON + 3)) / 3,     # 3-month average
            sum(lag(n) for n in range(HORIZON, HORIZON + 12)) / 12,   # 12-month average
            lag(HORIZON) / lag(HORIZON + 12) - 1,                    # year-on-year change
            lag(HORIZON) / lag(HORIZON + 1) - 1,                     # month-on-month change
            games[(last, market, "Slot machines total")] / total,
            games[(last, market, "Sports Pool")] / total,
            int(t[5:]),
            float(c["derived_days_in_month"]),
            float(c["derived_friday_saturday_nights"]),
            float(c["derived_federal_holidays"]),
        ]

    def model_factories():
        return {
            "Random Forest": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=0),
            "XGBoost": lambda: XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                                            subsample=0.8, colsample_bytree=0.8, random_state=0),
        }

    rows = []
    for market in MARKETS:
        train_months = [m for m in months if m not in EXCLUDED]  # filtered below to months published two months before each test month
        test_months = [m for m in months if m >= TEST_START]
        for t in test_months:
            train_X, train_y = [], []
            for m in train_months:
                if m > shift(t, -HORIZON):  # only months whose figures were known two months before t
                    continue
                x = inputs(m, market)
                if x is None:
                    continue
                train_X.append(x)
                train_y.append(math.log(first[(m, market)] / first[(shift(m, -12), market)]))
            test_x = inputs(t, market)
            if test_x is None or len(train_X) < 10:
                continue
            X, y = np.array(train_X), np.array(train_y)
            for name, make in model_factories().items():
                began = time.perf_counter()
                model = make().fit(X, y)
                ratio = float(model.predict(np.array([test_x]))[0])
                forecast = first[(shift(t, -12), market)] * math.exp(ratio)
                rows.append({"market": market, "model": name, "month": t, "forecast_m": round(forecast, 3),
                             "actual_m": round(latest[(t, market)], 3), "training_rows": len(train_X),
                             "fit_seconds": round(time.perf_counter() - began, 4)})

    MODEL.mkdir(parents=True, exist_ok=True)
    with (MODEL / "tree_models_backtest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Tree models, two months ahead, {TEST_START} onward\n")
    print(f"{'market':9} {'model':14} {'months':>6} {'min train':>9} {'MAE $m':>8} {'RMSE $m':>8} {'MAPE':>7}")
    for market in MARKETS:
        for name in model_factories():
            r = [x for x in rows if x["market"] == market and x["model"] == name]
            errs = [x["actual_m"] - x["forecast_m"] for x in r]
            mae = sum(abs(e) for e in errs) / len(errs)
            rmse = (sum(e * e for e in errs) / len(errs)) ** 0.5
            mape = sum(abs(x["actual_m"] - x["forecast_m"]) / x["actual_m"] for x in r) / len(r)
            print(f"{market:9} {name:14} {len(r):>6} {min(x['training_rows'] for x in r):>9} {mae:>8.2f} {rmse:>8.2f} {mape:>7.1%}")


if __name__ == "__main__":
    main()
