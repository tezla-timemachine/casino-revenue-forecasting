"""All models on one test window, using the longer history (2015 to 2019 and 2022 onward).

Test window: March 2023 to September 2026 (43 months), two months ahead (D19). Every model uses only
figures published by then. Training history: January 2015 onward, with 2020 and 2021 left out (D23),
treated as missing in the fit, so the model never learns from the closures.

Models:
  baseline last published      forecast = figure two months back
  baseline same month last yr  forecast = figure twelve months back
  ARIMA                        no seasonal term
  SARIMA                       seasonal term repeating every 12 months
  SARIMA + calendar            calendar for the month forecast (known in advance)
  SARIMA + game mix            slot and sports-pool shares, two months back
  SARIMA + both

The order of each model is chosen by AIC from four options (d fixed at 1, the choice every fit made in earlier runs).

    .venv/bin/python scripts/compare_models.py

Writes data/model/model_comparison.csv (one row per forecast) and data/model/model_comparison.md (summary).
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
FEATURES = ROOT / "data" / "features"
MODEL = ROOT / "data" / "model"
MARKETS = ["LV Strip", "Reno"]
HORIZON = 2          # D19
SCALE = 1e6
TEST_START = "2023-03"
EXCLUDED = {f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)}  # D23
ORDERS = [(0, 1, 0), (0, 1, 1), (1, 1, 0), (1, 1, 1)]


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def best(y, exog, seasonal):
    """Fit each option and keep the lowest AIC. Returns the fitted result."""
    winner = None
    for order in ORDERS:
        try:
            if seasonal:
                model = SARIMAX(y, exog=exog, order=order, seasonal_order=(1, 0, 0, 12),
                                enforce_stationarity=True, enforce_invertibility=True)
                res = model.fit(disp=False)
            else:
                res = ARIMA(y, exog=exog, order=order).fit()
        except Exception:
            continue
        if winner is None or res.aic < winner.aic:
            winner = res
    return winner


def main() -> None:
    win = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) / SCALE for r in win}
    latest = {(r["month"], r["area"]): float(r["gaming_win"]) / SCALE for r in win}
    games = {(r["month"], r["area"], r["game"]): float(r["win_usd"]) for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv"))}
    cal = {r["month"]: r for r in csv.DictReader(open(FEATURES / "calendar.csv"))}
    months = sorted({r["month"] for r in win})
    targets = [m for m in months if m >= TEST_START]

    def mix(month, market):
        total = games.get((month, market, "Total gaming"))
        if not total:
            return None
        return [games[(month, market, "Slot machines total")] / total, games[(month, market, "Sports Pool")] / total]

    def calendar(month):
        c = cal[month]
        return [float(c["derived_days_in_month"]), float(c["derived_friday_saturday_nights"]), float(c["derived_federal_holidays"])]

    def exog_for(t, market, use):
        row = []
        if "mix" in use:
            share = mix(shift(t, -HORIZON), market)
            if share is None:
                return None
            row += share
        if "cal" in use:
            row += calendar(t)
        return row

    def history(target, market, use):
        """Y and exog for every month up to two months before the target. Left-out months become NaN."""
        known_end = shift(target, -HORIZON)
        width = (2 if "mix" in use else 0) + (3 if "cal" in use else 0)
        ys, xs = [], []
        for m in months:
            if m > known_end:
                break
            y = np.nan if m in EXCLUDED else first[(m, market)]
            if use:
                x = exog_for(m, market, use)
                if x is None:  # game-mix shares missing for this month: leave the month out of the fit
                    y, x = np.nan, [0.0] * width
                xs.append(x)
            ys.append(y)
        return np.array(ys, dtype=float), (np.array(xs, dtype=float) if use else None)

    variants = {
        "SARIMA": (True, []),
        "SARIMA + calendar": (True, ["cal"]),
        "SARIMA + game mix": (True, ["mix"]),
        "SARIMA + both": (True, ["cal", "mix"]),
        "ARIMA": (False, []),
    }
    rows = []
    for market in MARKETS:
        for target in targets:
            # Baselines
            rows.append({"market": market, "model": "baseline last published", "month": target,
                         "forecast_m": first[(shift(target, -HORIZON), market)],
                         "actual_m": latest[(target, market)], "order": "", "fit_seconds": 0})
            rows.append({"market": market, "model": "baseline same month last year", "month": target,
                         "forecast_m": first[(shift(target, -12), market)],
                         "actual_m": latest[(target, market)], "order": "", "fit_seconds": 0})
            for name, (seasonal, use) in variants.items():
                t0 = time.perf_counter()
                y, X = history(target, market, use)
                future = None
                if use:
                    future = np.array([exog_for(shift(target, -1), market, use), exog_for(target, market, use)], dtype=float)
                res = best(y, X, seasonal)
                if res is None:
                    forecast = float("nan")
                    order = ""
                else:
                    forecast = float(res.get_forecast(steps=HORIZON, exog=future).predicted_mean[-1]) if use \
                        else float(res.get_forecast(steps=HORIZON).predicted_mean[-1])
                    order = str(res.model.order) + (str(res.model.seasonal_order) if seasonal else "")
                rows.append({"market": market, "model": name, "month": target, "forecast_m": forecast,
                             "actual_m": latest[(target, market)], "order": order,
                             "fit_seconds": round(time.perf_counter() - t0, 3)})
            print(f"done {market} {target}", flush=True)

    MODEL.mkdir(parents=True, exist_ok=True)
    with (MODEL / "model_comparison.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [f"# Model comparison, two months ahead, {targets[0]} to {targets[-1]} ({len(targets)} months)", "",
             "Training history: 2015 onward, with 2020 and 2021 excluded (D23).", "",
             "| Market | Model | MAE ($m) | RMSE ($m) | MAPE | Seconds per forecast |", "|---|---|---|---|---|---|"]
    order = ["baseline last published", "baseline same month last year", "ARIMA", "SARIMA",
             "SARIMA + calendar", "SARIMA + game mix", "SARIMA + both"]
    for market in MARKETS:
        for name in order:
            r = [x for x in rows if x["market"] == market and x["model"] == name and np.isfinite(x["forecast_m"])]
            errs = [x["actual_m"] - x["forecast_m"] for x in r]
            mae = sum(abs(e) for e in errs) / len(errs)
            rmse = (sum(e * e for e in errs) / len(errs)) ** 0.5
            mape = sum(abs(x["actual_m"] - x["forecast_m"]) / x["actual_m"] for x in r) / len(r)
            sec = sum(x["fit_seconds"] for x in r) / len(r)
            lines.append(f"| {market} | {name} | {mae:.2f} | {rmse:.2f} | {mape:.1%} | {sec:.3f} |")
    (MODEL / "model_comparison.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
