"""ARIMA forecasts for the LV Strip and Reno, on the same two-months-ahead backtest as the baseline (D19).

For each month T, the model is fitted only on first-published figures up to two months before T, and it
forecasts T. The order of the model is chosen each time by AIC (a lower score means a better fit for the
same data, after allowing for complexity), from a small set of options.

Two versions:
  ARIMA (no seasonal term): the backtest starts March 2023, the first month with enough history.
  SARIMA (seasonal term, repeats every 12 months): starts January 2024, when two full years of history exist.
Both are compared with the baselines over the SAME months.

    .venv/bin/python scripts/arima_backtest.py

Writes data/model/arima_backtest.csv and prints the metrics. Needs statsmodels (in .venv).
"""
from __future__ import annotations

import csv
import itertools
import time
import warnings
from pathlib import Path

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "data" / "model" / "arima_backtest.csv"
MARKETS = ["LV Strip", "Reno"]
HORIZON = 2          # decision D19
SCALE = 1e6          # fit in millions of dollars for numerical stability
ARIMA_START, SARIMA_START = "2023-03", "2024-01"
ORDERS = list(itertools.product([0, 1], [0, 1], [0, 1]))  # (p, d, q) options


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def best_fit(y: np.ndarray, seasonal: bool):
    """Return the fitted result with the lowest AIC among the options."""
    best = None
    for p, d, q in ORDERS:
        try:
            if seasonal:
                model = SARIMAX(y, order=(p, d, q), seasonal_order=(1, 0, 0, 12),
                                enforce_stationarity=True, enforce_invertibility=True)
            else:
                model = ARIMA(y, order=(p, d, q))
            res = model.fit(disp=False) if seasonal else model.fit()
        except Exception:
            continue
        if best is None or res.aic < best.aic:
            best, best_order = res, (p, d, q)
    return best, best_order


def main() -> None:
    rows = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) / SCALE for r in rows}
    latest = {(r["month"], r["area"]): float(r["gaming_win"]) / SCALE for r in rows}
    months = sorted({r["month"] for r in rows})
    results = []
    for market in MARKETS:
        for name, seasonal, start in [("ARIMA", False, ARIMA_START), ("SARIMA", True, SARIMA_START)]:
            for target in [m for m in months if m >= start]:
                known_end = shift(target, -HORIZON)
                history = np.array([first[(m, market)] for m in months if m <= known_end])
                began = time.perf_counter()
                res, order = best_fit(history, seasonal)
                forecast = float(res.get_forecast(steps=HORIZON).predicted_mean[-1])
                seconds = time.perf_counter() - began
                results.append({"market": market, "model": name, "month": target,
                                "forecast_m": round(forecast, 3), "actual_m": round(latest[(target, market)], 3),
                                "order": f"{order}" + (" x (1,0,0,12)" if seasonal else ""),
                                "fit_seconds": round(seconds, 3)})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    def score(market, model, start):
        pairs = [(r["actual_m"], r["forecast_m"]) for r in results
                 if r["market"] == market and r["model"] == model and r["month"] >= start]
        errs = [a - f for a, f in pairs]
        return (len(pairs), sum(abs(e) for e in errs) / len(errs), (sum(e * e for e in errs) / len(errs)) ** 0.5,
                sum(abs(e) / a for e, (a, _) in zip(errs, pairs)) / len(pairs),
                sum(r["fit_seconds"] for r in results if r["market"] == market and r["model"] == model) / len(pairs))

    print("Backtest for each model over its own months, and the baseline over the same months\n")
    print(f"{'market':9} {'model':16} {'from':8} {'months':>6} {'MAE $m':>8} {'RMSE $m':>8} {'MAPE':>7} {'sec/fit':>8}")
    for market in MARKETS:
        for model, start in [("ARIMA", ARIMA_START), ("SARIMA", SARIMA_START)]:
            n, mae, rmse, mape, sec = score(market, model, start)
            print(f"{market:9} {model:16} {start:8} {n:>6} {mae:>8.2f} {rmse:>8.2f} {mape:>7.1%} {sec:>8.3f}")
        # same-month-last-year baseline over the SARIMA window (2024-01 onward) for a like-for-like comparison
        base = [(latest[(m, market)], latest_shift(first, m, market)) for m in months if m >= SARIMA_START]
        errs = [a - f for a, f in base]
        print(f"{market:9} {'baseline (last yr)':16} {SARIMA_START:8} {len(base):>6} "
              f"{sum(abs(e) for e in errs)/len(errs):>8.2f} {(sum(e*e for e in errs)/len(errs))**0.5:>8.2f} "
              f"{sum(abs(e)/a for e, (a, _) in zip(errs, base))/len(base):>7.1%} {'':>8}")
    print(f"\nWritten: {OUT.relative_to(ROOT)}")


def latest_shift(first, month, market):
    """Same month last year, as first published (the baseline's own rule). 'first' is already in millions."""
    return first[(shift(month, -12), market)]


if __name__ == "__main__":
    main()
