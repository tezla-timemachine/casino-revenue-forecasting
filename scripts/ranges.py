"""80% range around each forecast, from the model's own past misses (D53).

A past miss is actual / forecast - 1. The range drops the worst 10% of misses on each side:
    low  = forecast x (1 + 10th percentile of past misses)
    high = forecast x (1 + 90th percentile of past misses)
Only misses known when the forecast is made count: target months up to two before the new target (D19).
A model needs at least MIN_PAST misses, otherwise it gets no range.

History used:
  same month last year   every month from 2016 (93 by Sep 2026); months where this year or last year falls
                         in 2020-21 are left out (D23)
  other models           their backtest months from March 2023 (data/model/model_comparison.csv,
                         data/model/bottom_up_backtest.csv)
Actuals are the newest figures, as in the backtest.

    .venv/bin/python scripts/ranges.py     # prints the November 2026 ranges and how often past ranges held
"""
from __future__ import annotations

import csv
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bottom_up as bu  # a Challenger since D51

ROOT = Path(__file__).resolve().parents[1]
CLEAN, MODEL = ROOT / "data" / "clean", ROOT / "data" / "model"
LEVEL, LOW_Q, HIGH_Q = "80%", 10, 90
HORIZON, MIN_PAST, HISTORY_FROM = 2, 12, "2016-01"
EXCLUDED = {f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)}
BASELINE = "baseline same month last year"


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    t = y * 12 + (m - 1) + n
    return f"{t // 12}-{t % 12 + 1:02d}"


@lru_cache(maxsize=None)
def misses(market: str, model: str) -> tuple:
    """(target month, actual / forecast - 1) for every month the model has been scored on, oldest first."""
    if model == BASELINE:
        win = {(r["month"], r["area"]): r for r in csv.DictReader(open(CLEAN / "monthly_win.csv"))}
        months = sorted(m for (m, a) in win if a == market and m >= HISTORY_FROM and m not in EXCLUDED
                        and shift(m, -12) not in EXCLUDED and (shift(m, -12), a) in win)
        return tuple((m, float(win[(m, market)]["gaming_win"]) / float(win[(shift(m, -12), market)]["first_published"]) - 1)
                     for m in months)
    out = [(r["month"], float(r["actual_m"]) / float(r["forecast_m"]) - 1)
           for r in csv.DictReader(open(MODEL / "model_comparison.csv")) if r["market"] == market and r["model"] == model]
    if model == bu.NAME_A:
        out = [(r["month"], float(r["actual_m"]) / float(r["A_baccarat_luck_out_m"]) - 1)
               for r in csv.DictReader(open(MODEL / "bottom_up_backtest.csv")) if r["market"] == market and r["A_baccarat_luck_out_m"]]
    return tuple(sorted(out))


def forecast_range(market: str, model: str, target: str, forecast: float):
    """(low, high) for a forecast of `target`, or (None, None) if the model has too few past misses."""
    past = [x for m, x in misses(market, model) if m <= shift(target, -HORIZON)]
    if len(past) < MIN_PAST or forecast in (None, ""):
        return None, None
    f = float(forecast)
    return f * (1 + np.percentile(past, LOW_Q)), f * (1 + np.percentile(past, HIGH_Q))


def main() -> None:
    rows = list(csv.DictReader(open(MODEL / "model_comparison.csv")))
    for market, model in [("LV Strip", BASELINE), ("LV Strip", "SARIMA + both"), ("LV Strip", bu.NAME_A),
                          ("Reno", BASELINE), ("Reno", "SARIMA + game mix")]:
        if model == bu.NAME_A:
            fc = {r["month"]: (float(r["A_baccarat_luck_out_m"]), float(r["actual_m"])) for r in csv.DictReader(open(MODEL / "bottom_up_backtest.csv"))
                  if r["market"] == market and r["A_baccarat_luck_out_m"]}
        else:
            fc = {r["month"]: (float(r["forecast_m"]), float(r["actual_m"])) for r in rows if r["market"] == market and r["model"] == model}
        held = [lo <= a <= hi for m, (f, a) in sorted(fc.items()) for lo, hi in [forecast_range(market, model, m, f)] if lo is not None]
        print(f"{market:9} {model:30} {len(misses(market, model)):>3} past misses | held {sum(held)}/{len(held)} = {sum(held) / len(held):.0%}")


if __name__ == "__main__":
    main()
