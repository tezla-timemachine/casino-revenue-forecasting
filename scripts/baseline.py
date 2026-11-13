"""Baseline forecasts for the LV Strip and Reno, tested by backtesting (no random splits).

For each month from January 2023 to September 2026, each baseline forecasts that month using only
the figures that were known before it. Inputs use the FIRST-PUBLISHED figures (what the Board had
published at the time). Actuals are the newest figures (the best known truth today).

Two months ahead (decision D19): the newest figure available is two months before the month forecast.

Baselines:
  last published   the forecast is the figure from two months before (the brief's simplest example)
  same month last year   the forecast is the same month last year (captures the seasonal pattern)

Writes data/model/baseline_backtest.csv and prints the metrics. Standard library only.
"""
from __future__ import annotations

import csv
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "clean" / "monthly_win.csv"
OUT = ROOT / "data" / "model" / "baseline_backtest.csv"
MARKETS = ["LV Strip", "Reno"]
FIRST_TARGET = "2023-03"  # same start as the feature table


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def forecast_last_published(known: dict, target: str) -> float:
    return known[shift(target, -2)]


def forecast_same_month_last_year(known: dict, target: str) -> float:
    return known[shift(target, -12)]


BASELINES = {"last published": forecast_last_published,
             "same month last year": forecast_same_month_last_year}


def metrics(pairs: list[tuple[float, float]]) -> dict:
    errors = [a - f for a, f in pairs]
    return {
        "months": len(pairs),
        "MAE_m": sum(abs(e) for e in errors) / len(errors) / 1e6,
        "RMSE_m": math.sqrt(sum(e * e for e in errors) / len(errors)) / 1e6,
        "MAPE": sum(abs(e) / a for e, (a, _) in zip(errors, pairs)) / len(pairs),
    }


def main() -> None:
    rows = list(csv.DictReader(open(TABLE)))
    first = {(r["month"], r["area"]): float(r["first_published"]) for r in rows}
    latest = {(r["month"], r["area"]): float(r["gaming_win"]) for r in rows}
    months = sorted({r["month"] for r in rows})
    targets = [m for m in months if m >= FIRST_TARGET]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for market in MARKETS:
        known = {m: first[(m, market)] for m in months}  # what was known at the time
        for name, fn in BASELINES.items():
            for target in targets:
                start = time.perf_counter()
                predicted = fn(known, target)
                seconds = time.perf_counter() - start
                actual = latest[(target, market)]
                results.append({"market": market, "baseline": name, "month": target,
                                "forecast": round(predicted), "actual": round(actual),
                                "error_pct": f"{(actual - predicted) / actual:+.2%}",
                                "forecast_seconds": f"{seconds:.6f}"})

    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    print(f"Backtest: {targets[0]} to {targets[-1]} ({len(targets)} months)\n")
    print(f"{'market':10} {'baseline':22} {'months':>6} {'MAE $m':>8} {'RMSE $m':>8} {'MAPE':>7}")
    for market in MARKETS:
        for name in BASELINES:
            pairs = [(float(r["actual"]), float(r["forecast"])) for r in results
                     if r["market"] == market and r["baseline"] == name]
            m = metrics(pairs)
            print(f"{market:10} {name:22} {m['months']:>6} {m['MAE_m']:>8.2f} {m['RMSE_m']:>8.2f} {m['MAPE']:>7.1%}")
    print(f"\nWritten: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
