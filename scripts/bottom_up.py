"""Bottom-up forecasts: forecast each game type separately, then add them up (D50, D51).

The idea: casinos keep a near-steady share of what is bet on slots, but baccarat hold (the share kept) swings
with luck. So instead of copying last year's baccarat WIN (which copies last year's luck), copy last year's
AMOUNT BET and apply a normal hold: the average hold over the 24 newest months known at the time.

Methods, two months ahead (D19), on the same 43 test months as the other models:
  production              same month last year (for comparison)
  A: baccarat luck out    slots and other tables as last year; baccarat = last year's amount bet x normal baccarat hold
  B: all tables luck out  slots as last year; all tables = last year's amount bet x normal table hold

Amount bet = win / hold (the Board's "win percent"). Inputs are each month's own report (first published).
Results are scored against the newest total win, as in the backtest.

    .venv/bin/python scripts/bottom_up.py            # backtest, writes data/model/bottom_up_backtest.csv
    .venv/bin/python scripts/bottom_up.py --mlflow   # also records the runs in MLflow
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN, MODEL = ROOT / "data" / "clean", ROOT / "data" / "model"
HORIZON, TEST_START, HOLD_WINDOW = 2, "2023-03", 24
NAME_A = "bottom-up baccarat luck out"


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    t = y * 12 + (m - 1) + n
    return f"{t // 12}-{t % 12 + 1:02d}"


def load() -> dict:
    win = {(r["month"], r["area"]): r for r in csv.DictReader(open(CLEAN / "monthly_win.csv"))}
    return {"win": win,
            "games": {(r["month"], r["area"], r["game"]): float(r["win_usd"]) / 1e6 for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv"))},
            "cap": {(r["month"], r["area"]): r for r in csv.DictReader(open(CLEAN / "capacity_hold_monthly.csv"))},
            "months": sorted({m for m, _ in win})}


def parts(d: dict, m: str, market: str):
    """Slots, baccarat and other tables (win, $m), plus baccarat and table hold (%), from month m's own report."""
    slots, tables = d["games"].get((m, market, "Slot machines total")), d["games"].get((m, market, "Table games total"))
    bacc = d["games"].get((m, market, "Baccarat"), 0.0)
    c = d["cap"].get((m, market))
    if slots is None or tables is None or c is None:
        return None
    h_b = float(c["baccarat_hold_pct"]) if c["baccarat_hold_pct"] not in ("", "None") else None
    return {"slots": slots, "bacc": bacc, "other": tables - bacc, "tables": tables, "h_bacc": h_b, "h_table": float(c["table_hold_pct"])}


def normal_hold(d: dict, target: str, market: str, key: str):
    """Average hold over the newest HOLD_WINDOW months published two months before the target."""
    known = [m for m in d["months"] if m <= shift(target, -HORIZON)]
    vals = [p[key] for m in reversed(known) if (p := parts(d, m, market)) and p[key] is not None][:HOLD_WINDOW]
    return sum(vals) / len(vals) if vals else None


def forecast_a(d: dict, market: str, target: str):
    """Method A: baccarat at normal hold. None when the inputs are missing."""
    last = parts(d, shift(target, -12), market)
    if not last or not last["h_bacc"]:
        return None
    bet = last["bacc"] / (last["h_bacc"] / 100)
    return last["slots"] + last["other"] + bet * normal_hold(d, target, market, "h_bacc") / 100


def forecast_b(d: dict, market: str, target: str):
    """Method B: all tables at normal hold."""
    last = parts(d, shift(target, -12), market)
    if not last:
        return None
    return last["slots"] + last["tables"] / (last["h_table"] / 100) * normal_hold(d, target, market, "h_table") / 100


def next_forecast(market: str):
    """Method A's forecast for two months after the newest published month: (target month, $m or None)."""
    d = load()
    target = shift(d["months"][-1], HORIZON)
    return target, forecast_a(d, market, target)


def metrics(pts):
    e = [a - f for a, f in pts]
    return {"MAPE_pct": sum(abs(x) / a for x, (a, _) in zip(e, pts)) / len(e) * 100, "MAE_m": sum(abs(x) for x in e) / len(e),
            "RMSE_m": (sum(x * x for x in e) / len(e)) ** 0.5, "bias_m": sum(e) / len(e),
            "MAPE_last12_pct": sum(abs(a - f) / a for a, f in pts[-12:]) / len(pts[-12:]) * 100}


def log_mlflow(rows: list[dict]) -> None:
    """Record method A (Strip) and B (Reno) as MLflow runs alongside the other 18 (Step 7)."""
    import os
    os.environ.update(MLFLOW_DISABLE_TELEMETRY="true", DO_NOT_TRACK="true", MLFLOW_DISABLE_AGENT_HINT="1")
    import tempfile
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mlflow
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow' / 'mlflow.db'}")
    mlflow.set_experiment("Week 4 revenue forecasting: backtest, two months ahead")
    for market, col, name, desc in [("LV Strip", "A_baccarat_luck_out_m", NAME_A, "Slots and other tables as last year; baccarat = last year's amount bet x 24-month average baccarat hold"),
                                     ("Reno", "B_tables_luck_out_m", "bottom-up tables luck out", "Slots as last year; tables = last year's amount bet x 24-month average table hold")]:
        r = [x for x in rows if x["market"] == market and x.get(col) not in (None, "")]
        pts = [(x["actual_m"], x[col]) for x in r]
        with mlflow.start_run(run_name=f"{market} | {name}"):
            mlflow.set_tags({"market": market, "model": name, "role": "candidate", "decisions": "D50, D51"})
            mlflow.log_params({"model": name, "market": market, "description": desc, "hold_window_months": HOLD_WINDOW,
                               "training_period": "no training: last year's figures and a 24-month hold average known two months before",
                               "test_period": f"{r[0]['month']} to {r[-1]['month']} ({len(r)} months)", "horizon_months": HORIZON,
                               "features": "slot win, table win, baccarat win and hold, 12 months before; hold history", "retraining": "none (a rule)"})
            mlflow.log_metrics(metrics(pts))
            with tempfile.TemporaryDirectory() as tmp:
                fig, ax = plt.subplots(figsize=(10, 4)); xs = [x["month"] for x in r]
                ax.plot(xs, [a for a, _ in pts], color="#1f3b57", lw=2, label="Actual"); ax.plot(xs, [f for _, f in pts], color="#d98c1f", label=name)
                ax.set_xticks(xs[::3]); ax.tick_params(axis="x", rotation=45, labelsize=8); ax.legend(frameon=False); ax.grid(alpha=0.25)
                ax.set_title(f"{market}: {name}, MAPE {metrics(pts)['MAPE_pct']:.1f}%"); fig.tight_layout()
                fig.savefig(Path(tmp) / "forecast_chart.png", dpi=120); plt.close(fig)
                mlflow.log_artifact(str(Path(tmp) / "forecast_chart.png"))
        print(f"MLflow: logged {market} | {name}")


def main() -> None:
    d = load()
    rows = []
    for market in ["LV Strip", "Reno"]:
        for t in [m for m in d["months"] if m >= TEST_START]:
            out = {"market": market, "month": t, "actual_m": round(float(d["win"][(t, market)]["gaming_win"]) / 1e6, 3),
                   "production_m": round(float(d["win"][(shift(t, -12), market)]["first_published"]) / 1e6, 3)}
            a, b = forecast_a(d, market, t), forecast_b(d, market, t)
            if a is not None:
                out["A_baccarat_luck_out_m"] = round(a, 3)
            if b is not None:
                out["B_tables_luck_out_m"] = round(b, 3)
            rows.append(out)
    with (MODEL / "bottom_up_backtest.csv").open("w", newline="") as fh:
        fields = ["market", "month", "actual_m", "production_m", "A_baccarat_luck_out_m", "B_tables_luck_out_m"]
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"{'market':9} {'method':26} {'MAPE':>7} {'MAE $m':>7} {'RMSE $m':>8} {'bias $m':>8} {'last 12':>8}")
    for market in ["LV Strip", "Reno"]:
        r = [x for x in rows if x["market"] == market]
        for col, name in [("production_m", "production (last year)"), ("A_baccarat_luck_out_m", "A: baccarat luck out"), ("B_tables_luck_out_m", "B: all tables luck out")]:
            pts = [(x["actual_m"], x[col]) for x in r if x.get(col) not in (None, "")]
            if pts:
                m = metrics(pts)
                print(f"{market:9} {name:26} {m['MAPE_pct']:>6.2f}% {m['MAE_m']:>7.1f} {m['RMSE_m']:>8.1f} {m['bias_m']:>+8.1f} {m['MAPE_last12_pct']:>7.2f}%")
    if "--mlflow" in sys.argv:
        log_mlflow(rows)


if __name__ == "__main__":
    main()
