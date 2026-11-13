"""Next forecast for each market, from the production model and its Challenger.

With the newest published month M, the next forecast is for M + 2 (decision D19). Inputs use first-published
figures, as in the backtest. Champion: same month last year. Challengers: Seasonal ARIMA + both (Strip),
Seasonal ARIMA + game mix (Reno), fitted exactly as in scripts/compare_models.py.

    .venv/bin/python scripts/forecast_next.py

Prints the forecasts and writes data/model/next_forecasts.csv.
"""
from __future__ import annotations

import csv
import warnings
from pathlib import Path

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
CLEAN, FEATURES, MODEL = ROOT / "data" / "clean", ROOT / "data" / "features", ROOT / "data" / "model"
HORIZON = 2
EXCLUDED = {f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)}
ORDERS = [(0, 1, 0), (0, 1, 1), (1, 1, 0), (1, 1, 1)]
CHALLENGERS = {"LV Strip": ("SARIMA + both", ["cal", "mix"]), "Reno": ("SARIMA + game mix", ["mix"])}


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def next_forecasts() -> list[dict]:
    """Forecasts for the month two after the newest published month, from each market's Champion and Challenger."""
    win = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) / 1e6 for r in win}
    games = {(r["month"], r["area"], r["game"]): float(r["win_usd"]) for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv"))}
    cal = {r["month"]: r for r in csv.DictReader(open(FEATURES / "calendar.csv"))}
    months = sorted({r["month"] for r in win})
    newest = months[-1]
    target = shift(newest, HORIZON)

    def exog(t, market, use):
        row = []
        if "mix" in use:
            m = shift(t, -HORIZON)
            total = games.get((m, market, "Total gaming"))
            if not total:
                return None
            row += [games[(m, market, "Slot machines total")] / total, games[(m, market, "Sports Pool")] / total]
        if "cal" in use:
            c = cal[t]
            row += [float(c["derived_days_in_month"]), float(c["derived_friday_saturday_nights"]), float(c["derived_federal_holidays"])]
        return row

    out = []
    for market, (name, use) in CHALLENGERS.items():
        champion = first[(shift(target, -12), market)]
        width = (2 if "mix" in use else 0) + (3 if "cal" in use else 0)
        ys, xs = [], []
        for m in months:
            y = np.nan if m in EXCLUDED else first[(m, market)]
            x = exog(m, market, use)
            if x is None:
                y, x = np.nan, [0.0] * width
            ys.append(y); xs.append(x)
        future = [exog(shift(target, -1), market, use), exog(target, market, use)]
        challenger, order = None, ""
        if None not in future:  # the Challenger needs its inputs for the months ahead
            best = None
            for o in ORDERS:
                try:
                    res = SARIMAX(np.array(ys), exog=np.array(xs, dtype=float), order=o, seasonal_order=(1, 0, 0, 12),
                                  enforce_stationarity=True, enforce_invertibility=True).fit(disp=False)
                except Exception:
                    continue
                if best is None or res.aic < best.aic:
                    best = res
            challenger = float(best.get_forecast(steps=HORIZON, exog=np.array(future, dtype=float)).predicted_mean[-1])
            order = str(best.model.order)
        out.append({"market": market, "forecast_month": target, "made_with_data_to": newest,
                    "champion_same_month_last_year_m": round(champion, 1), "challenger_model": name,
                    "challenger_m": round(challenger, 1) if challenger is not None else "", "challenger_order": order})
    return out


def main() -> None:
    out = next_forecasts()
    for r in out:
        print(f"{r['market']}: forecast for {r['forecast_month']} (data to {r['made_with_data_to']}) | "
              f"Champion ${r['champion_same_month_last_year_m']}m | {r['challenger_model']} ${r['challenger_m']}m")
    with (MODEL / "next_forecasts.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)


if __name__ == "__main__":
    main()
