"""Seasonal ARIMA with extra inputs (SARIMAX), two months ahead (D19), for the LV Strip and Reno.

Inputs known in time for a forecast of month T:
  - game-mix shares (slots and sports pool as a share of total win) for month T-2, the newest published month.
    The model learns how the share two months earlier relates to win this month.
  - calendar features for month T itself (days in the month, Friday and Saturday nights, federal holidays).
    These are known in advance, so they are safe to use.

Three versions are compared with each other, the plain seasonal model and the baseline, over the same months
(January 2024 onward, when two years of history exist for the seasonal term):
  calendar only, game mix only, both.

    .venv/bin/python scripts/sarima_features.py

Writes data/model/sarima_features_backtest.csv and prints the metrics. Needs statsmodels (in .venv).
"""
from __future__ import annotations

import csv
import itertools
import warnings
from pathlib import Path

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
FEATURES = ROOT / "data" / "features"
OUT = ROOT / "data" / "model" / "sarima_features_backtest.csv"
MARKETS = ["LV Strip", "Reno"]
HORIZON = 2
SCALE = 1e6
START = "2024-01"
ORDERS = list(itertools.product([0, 1], [0, 1], [0, 1]))
VERSIONS = {"SARIMA + calendar": ["cal"], "SARIMA + game mix": ["mix"], "SARIMA + both": ["cal", "mix"]}


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

    def mix(month, market):  # game-mix shares for a month
        total = games[(month, market, "Total gaming")]
        return [games[(month, market, "Slot machines total")] / total, games[(month, market, "Sports Pool")] / total]

    def calendar(month):
        c = cal[month]
        return [float(c["derived_days_in_month"]), float(c["derived_friday_saturday_nights"]), float(c["derived_federal_holidays"])]

    def exog_row(t, market, use):
        row = []
        if "mix" in use:
            row += mix(shift(t, -HORIZON), market)  # the share two months before t
        if "cal" in use:
            row += calendar(t)                      # calendar for t itself
        return row

    results = []
    for market in MARKETS:
        for name, use in VERSIONS.items():
            for target in [m for m in months if m >= START]:
                known_end = shift(target, -HORIZON)
                history = [m for m in months if shift(m, HORIZON) <= known_end and m >= "2022-03"]
                y = np.array([first[(m, market)] for m in history])
                X = np.array([exog_row(m, market, use) for m in history])
                future = np.array([exog_row(shift(target, -1), market, use), exog_row(target, market, use)])
                best = None
                for p, d, q in ORDERS:
                    try:
                        res = SARIMAX(y, exog=X, order=(p, d, q), seasonal_order=(1, 0, 0, 12),
                                      enforce_stationarity=True, enforce_invertibility=True).fit(disp=False)
                    except Exception:
                        continue
                    if best is None or res.aic < best.aic:
                        best = res
                forecast = float(best.get_forecast(steps=HORIZON, exog=future).predicted_mean[-1])
                results.append({"market": market, "model": name, "month": target,
                                "forecast_m": round(forecast, 3), "actual_m": round(latest[(target, market)], 3),
                                "history_months": len(history)})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    def mape(pairs):
        return sum(abs(a - f) / a for a, f in pairs) / len(pairs)

    print(f"Two months ahead, {START} to {results[-1]['month']} (33 months)\n")
    print(f"{'market':9} {'model':20} {'MAE $m':>8} {'MAPE':>7}")
    for market in MARKETS:
        for name in VERSIONS:
            rows = [r for r in results if r["market"] == market and r["model"] == name]
            pairs = [(r["actual_m"], r["forecast_m"]) for r in rows]
            mae = sum(abs(a - f) for a, f in pairs) / len(pairs)
            print(f"{market:9} {name:20} {mae:>8.2f} {mape(pairs):>7.1%}")
        base = [(latest[(m, market)], first[(shift(m, -12), market)]) for m in months if m >= START]
        print(f"{market:9} {'baseline (last yr)':20} {sum(abs(a-f) for a,f in base)/len(base):>8.2f} {mape(base):>7.1%}")
    print(f"\nWritten: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
