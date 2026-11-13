"""Monthly monitoring for the LV Strip and Reno forecasts.

Each run happens when the Board publishes a new month. For each market it:
  1. checks the new month's data before using it (D38)
  2. scores the forecasts made two months earlier against the actual figure
  3. tracks 12-month MAPE, MAE, RMSE and bias for the production model (D31)
  4. raises the fast, slow and capacity alerts (D37) and sets the status: Healthy, Investigate or Data issue
  5. runs the promotion check, Champion against each Challenger (D32, D33); if two pass together,
     the one with the lower 12-month MAPE is recommended (D51)
  6. on the live run, makes the next forecast from the production model, with a fallback (D34, D38),
     records the model version and last retraining date (D39)
  7. puts an 80% range around every forecast, from the model's own past misses, and tracks how often
     the actual lands inside it; too few inside raises the range alert (D53)

    .venv/bin/python scripts/monitor.py

The replay covers every test month (March 2023 onward), as if monitoring had been running, using the
forecasts already made in the backtest. The last month is the live run. Thresholds come from each model's
43-month test history, so the replay uses hindsight for them; live runs use the same fixed values.

Writes data/monitoring/monthly_status.csv, forecast_log.csv and report_<month>.md.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forecast_next as fn  # next forecasts, fitted as in the backtest
import bottom_up as bu      # bottom-up forecasts (D50, D51)
import ranges as rg         # 80% ranges (D53)

ROOT = Path(__file__).resolve().parents[1]
CLEAN, EXTRACTED, MODEL = ROOT / "data" / "clean", ROOT / "data" / "extracted", ROOT / "data" / "model"
RAW, MON = ROOT / "data" / "raw", ROOT / "data" / "monitoring"
MARKETS = ["LV Strip", "Reno"]
COUNTIES = ["Clark County", "Washoe County", "Elko County"]
TEST_START = "2023-03"
MARGIN, LONG_TOLERANCE, RUN = 0.005, 0.0025, 3        # D32
SLOW_ABOVE, CAPACITY_CHANGE = 0.015, 0.05              # D37
LATE_DAYS = 7                                          # D38
RANGE_MIN_INSIDE = 7                                   # D53: alert at 7 or fewer of the last 12 inside the 80% range


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    t = y * 12 + (m - 1) + n
    return f"{t // 12}-{t % 12 + 1:02d}"


def metrics(pairs):
    """pairs of (actual, forecast) -> MAPE, MAE, RMSE, bias (average actual minus forecast)."""
    e = [a - f for a, f in pairs]
    return {"mape": sum(abs(x) / a for x, (a, _) in zip(e, pairs)) / len(e), "mae": sum(abs(x) for x in e) / len(e),
            "rmse": (sum(x * x for x in e) / len(e)) ** 0.5, "bias": sum(e) / len(e)}


def production_for(registry, market, forecast_month):
    entries = [e for e in registry[market] if e["from_forecast_month"] <= forecast_month]
    return entries[-1]


def main() -> None:
    MON.mkdir(parents=True, exist_ok=True)
    registry = json.loads((MON / "production.json").read_text())
    win = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) for r in win}
    by_month = {}
    for r in win:
        by_month.setdefault(r["month"], []).append(r)
    arr_months = Counter(r["report_month"] for name in ("manifest.csv", "manifest_2015-01_2019-12.csv")
                         for r in csv.DictReader(open(RAW / name)))
    method_a = {(r["report_month"], r["key"]): r for r in csv.DictReader(open(EXTRACTED / "method_a.csv"))}
    method_b = {(r["report_month"], r["key"]): r for r in csv.DictReader(open(EXTRACTED / "method_b.csv"))}
    games = {(r["month"], r["area"], r["game"]) for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv"))}
    game_problems = {tuple(m.groups()) for m in re.finditer(r"^- (\d{4}-\d{2}) ([A-Za-z ]+): (?!.*blank)", (CLEAN / "game_types_checks.md").read_text(), re.M)}
    capacity = {(r["month"], r["area"]): r for r in csv.DictReader(open(CLEAN / "capacity_hold_monthly.csv"))}
    forecasts = {(r["market"], r["model"], r["month"]): float(r["forecast_m"]) * 1e6
                 for r in csv.DictReader(open(MODEL / "model_comparison.csv"))}
    forecasts.update({(r["market"], bu.NAME_A, r["month"]): float(r["A_baccarat_luck_out_m"]) * 1e6
                      for r in csv.DictReader(open(MODEL / "bottom_up_backtest.csv")) if r["A_baccarat_luck_out_m"]})
    months = sorted(by_month)
    test_months = [m for m in months if m >= TEST_START]

    # Every model in a market's registry, Champion or Challenger, past or present: all are scored each month.
    models = {market: sorted({e["model"] for e in registry[market]} | {c for e in registry[market] for c in e["challengers"]})
              for market in MARKETS}

    # Thresholds from each model's own test history (D37).
    thresholds = {}
    for market in MARKETS:
        for model in models[market]:
            miss = sorted(abs(first[(m, market)] - forecasts[(market, model, m)]) / first[(m, market)] for m in test_months)
            thresholds[(market, model)] = {"bad_month": miss[int(0.9 * len(miss)) - 1], "normal": sum(miss) / len(miss)}

    (MON / "thresholds.json").write_text(json.dumps({f"{m}|{model}": v for (m, model), v in thresholds.items()}, indent=2))

    def data_check(month, market):
        """Checks on the new month (D38). Returns (failures that block the month, failures that block game-mix models)."""
        rows = by_month.get(month, [])
        fails = []
        if arr_months.get(month, 0) != 1:
            fails.append(f"month appears {arr_months.get(month, 0)} times in the downloads")
        if len(rows) != 20:
            fails.append(f"{len(rows)} areas instead of 20")
        val = {r["area"]: float(r["first_published"]) for r in rows}
        if any(v <= 0 for v in val.values()):
            fails.append("zero or negative value")
        for county in COUNTIES:
            parts = [float(r["first_published"]) for r in rows if r["parent"] == county]
            if county in val and abs(sum(parts) - val[county]) > 10:
                fails.append(f"{county} parts don't add up")
        top = [float(r["first_published"]) for r in rows if r["parent"] == "Statewide"]
        if "Statewide" in val and abs(sum(top) - val["Statewide"]) > 10:
            fails.append("counties don't add up to statewide")
        keys = [k for (m, k) in method_a if m == month]
        if keys and any(method_a[(month, k)] != {**method_b.get((month, k), {}), "file": method_a[(month, k)]["file"]} for k in keys):
            fails.append("the two readers disagree")
        mix_fails = []
        if (month, market, "Total gaming") not in games or (month, market) in game_problems:
            mix_fails.append("game-mix data missing or failing its checks")
        return fails, mix_fails

    status_rows, scored = [], {m: {} for m in MARKETS}
    run_count = {}  # (market, challenger) -> months in a row passing
    inside = {m: [] for m in MARKETS}  # did each month's actual land inside the production forecast's range?
    for month in test_months:
        for market in MARKETS:
            prod = production_for(registry, market, month)
            champ, challs = prod["model"], prod["challengers"]
            fails, mix_fails = data_check(month, market)
            row = {"data_to": month, "market": market, "model": champ, "version": prod["version"], "challenger": " / ".join(challs),
                   "data_check": "; ".join(fails + mix_fails) or "pass"}
            if fails:
                row.update(status="Data issue", alerts="data check failed")
                status_rows.append(row)
                continue
            actual = first[(month, market)]
            for model in models[market]:
                if (market, model, month) in forecasts and not (mix_fails and model != "baseline same month last year"):
                    scored[market].setdefault(model, []).append((month, actual, forecasts[(market, model, month)]))
            hist = scored[market][champ]
            f = forecasts[(market, champ, month)]
            row.update(actual_m=round(actual / 1e6, 1), forecast_m=round(f / 1e6, 1), miss_pct=f"{(actual - f) / actual:+.1%}")
            lo, hi = rg.forecast_range(market, champ, month, f)
            if lo is not None:
                inside[market].append(lo <= actual <= hi)
                row.update(range_low_m=round(lo / 1e6, 1), range_high_m=round(hi / 1e6, 1), in_range="yes" if lo <= actual <= hi else "no")
            if len(inside[market]) >= 12:
                row["in_range_12m"] = f"{sum(inside[market][-12:])} of 12"
            last12 = [(a, ff) for _, a, ff in hist[-12:]]
            if len(last12) >= 3:
                m12 = metrics(last12)
                row.update(mape_12m=f"{m12['mape']:.2%}", mae_12m_m=round(m12["mae"] / 1e6, 1),
                           rmse_12m_m=round(m12["rmse"] / 1e6, 1), bias_12m_m=round(m12["bias"] / 1e6, 1))
            th = thresholds[(market, champ)]
            alerts = []
            recent = [abs(a - ff) / a for _, a, ff in hist[-3:]]
            if sum(x > th["bad_month"] for x in recent) >= 2:
                alerts.append(f"fast: 2 of last 3 months over {th['bad_month']:.1%}")
            if len(hist) >= 12 and metrics(last12)["mape"] > th["normal"] + SLOW_ABOVE:
                alerts.append(f"slow: 12-month MAPE over {th['normal'] + SLOW_ABOVE:.1%}")
            now, before = capacity.get((month, market)), capacity.get((shift(month, -12), market))
            if now and before:
                for f_ in ("table_units", "slot_units"):
                    if now[f_] and before[f_] and abs(float(now[f_]) / float(before[f_]) - 1) > CAPACITY_CHANGE:
                        alerts.append(f"capacity: {f_.replace('_units', 's')} {float(now[f_]) / float(before[f_]) - 1:+.1%} on a year earlier")
            if len(inside[market]) >= 12 and sum(inside[market][-12:]) <= RANGE_MIN_INSIDE:
                alerts.append(f"range: only {sum(inside[market][-12:])} of the last 12 months inside the 80% range")
            row["alerts"] = "; ".join(alerts)
            row["status"] = "Investigate" if alerts else "Healthy"
            # Promotion check (D32), each Challenger against the Champion: needs 12 scored months for both.
            checks, ready = [], []
            for chall in challs:
                ch_hist = scored[market].get(chall, [])
                if len(hist) < 12 or len(ch_hist) < 12:
                    continue
                c12, p12 = metrics([(a, ff) for _, a, ff in ch_hist[-12:]]), metrics(last12)
                cf, pf = metrics([(a, ff) for _, a, ff in ch_hist]), metrics([(a, ff) for _, a, ff in hist])
                ok = (c12["mape"] <= p12["mape"] - MARGIN and cf["mape"] <= pf["mape"] + LONG_TOLERANCE
                      and c12["rmse"] <= p12["rmse"] and abs(c12["bias"]) <= abs(p12["bias"]))
                run_count[(market, chall)] = run_count.get((market, chall), 0) + 1 if ok else 0
                checks.append(f"{chall}: " + (f"passes ({run_count[(market, chall)]} in a row)" if ok else "doesn't pass"))
                if run_count[(market, chall)] >= RUN:
                    ready.append((c12["mape"], chall))
            if checks:
                row["promotion_check"] = "; ".join(checks)
            if ready:
                mape12, chall = min(ready)  # tie-break: lower 12-month MAPE (D51)
                pick = f"{chall}" + (f" (lower 12-month MAPE, {mape12:.2%})" if len(ready) > 1 else "")
                upcoming = [e for e in registry[market] if e["from_forecast_month"] > month and e["model"] == chall
                            and e.get("approved_trigger_from", "9999") <= month]
                row["promotion_check"] += (f". Switch approved to {pick}: {upcoming[0]['version']} from the {upcoming[0]['from_forecast_month']} forecast ({upcoming[0]['decision'].split(' ')[0]})"
                                           if upcoming else f". Switch recommended to {pick}, needs Product Owner approval (D34)")
            status_rows.append(row)

    # Live run: the newest month, plus the next forecast from each market's production model.
    newest = months[-1]
    nxt = {r["market"]: r for r in fn.next_forecasts()}
    target = shift(newest, 2)
    log, today = [], dt.date.today()
    # Data for the next month (newest + 1) is due by the end of the month after it: the day before newest + 3 begins.
    due = dt.date(int(shift(newest, 3)[:4]), int(shift(newest, 3)[5:]), 1) - dt.timedelta(days=1)
    late = today > due + dt.timedelta(days=LATE_DAYS)
    rules = ("baseline same month last year", bu.NAME_A)  # no settings to re-learn
    def with_range(entry, market, model):
        lo, hi = rg.forecast_range(market, model, target, entry["forecast_m"])
        return {**entry, "range_low_m": round(lo, 1) if lo is not None else "", "range_high_m": round(hi, 1) if hi is not None else ""}

    for market in MARKETS:
        prod = production_for(registry, market, target)
        r = nxt[market]
        values = {"baseline same month last year": r["champion_same_month_last_year_m"], r["challenger_model"]: r["challenger_m"]}
        if bu.NAME_A in models[market]:
            bu_target, bu_value = bu.next_forecast(market)
            values[bu.NAME_A] = round(bu_value, 1) if bu_target == target and bu_value is not None else ""
        fails, mix_fails = data_check(newest, market)
        value, note = values.get(prod["model"], ""), ""
        if prod["model"] != "baseline same month last year" and (value == "" or mix_fails or fails):
            value, note = values["baseline same month last year"], "fallback to 'same month last year' (D34, D38)"
        used = "baseline same month last year" if note else prod["model"]
        log.append(with_range({"made_with_data_to": newest, "forecast_month": target, "market": market, "role": "production",
                               "model": prod["model"], "version": prod["version"], "forecast_m": value, "note": note,
                               "last_retrained": "not applicable" if prod["model"] in rules else newest}, market, used))
        for chall in prod["challengers"]:
            log.append(with_range({"made_with_data_to": newest, "forecast_month": target, "market": market, "role": "challenger",
                                   "model": chall, "version": "", "forecast_m": values.get(chall, ""),
                                   "note": "" if values.get(chall, "") != "" else "inputs missing",
                                   "last_retrained": "not applicable" if chall in rules else newest}, market, chall))

    with (MON / "monthly_status.csv").open("w", newline="") as fh:
        fields = ["data_to", "market", "model", "version", "challenger", "data_check", "actual_m", "forecast_m", "miss_pct",
                  "range_low_m", "range_high_m", "in_range", "in_range_12m", "mape_12m", "mae_12m_m", "rmse_12m_m", "bias_12m_m", "alerts", "status", "promotion_check"]
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(status_rows)
    with (MON / "forecast_log.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(log[0])); w.writeheader(); w.writerows(log)

    latest = [r for r in status_rows if r["data_to"] == newest]
    lines = [f"# Monitoring report: data to {newest}", "",
             f"Run on {today:%d %B %Y}. Next release (data for {shift(newest, 1)}) expected by {due:%d %B %Y}; "
             f"{'LATE: alert raised' if late else 'not late'} (D38).", "", "## This month", "",
             "| Market | Model in use (version) | Data check | Actual | Forecast | 80% range | Miss | Inside range (last 12) | 12-month MAPE | Bias (12 months) | Status | Alerts | Promotion check |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in latest:
        money = lambda k: f"${r[k]}m" if r.get(k) not in (None, "") else "-"
        rng = f"${r['range_low_m']}m to ${r['range_high_m']}m" if r.get("range_low_m") not in (None, "") else "-"
        lines.append(f"| {r['market']} | {r['model']} ({r['version']}) | {r['data_check']} | {money('actual_m')} | {money('forecast_m')} | {rng} | "
                     f"{r.get('miss_pct') or '-'} | {r.get('in_range_12m') or '-'} | {r.get('mape_12m') or '-'} | {money('bias_12m_m')} | **{r['status']}** | {r.get('alerts') or '-'} | {r.get('promotion_check') or '-'} |")
    lines += ["", f"## Next forecast: {target}", "", "8 months in 10, the actual should land inside the 80% range (D53).", "",
              "| Market | Role | Model | Version | Forecast | 80% range | Last retrained (data to) | Note |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r['market']} | {r['role']} | {r['model']} | {r['version']} | ${r['forecast_m']}m | "
              + (f"${r['range_low_m']}m to ${r['range_high_m']}m" if r["range_low_m"] != "" else "-")
              + f" | {r['last_retrained']} | {r['note'] or '-'} |" for r in log]
    lines += ["", "## Replay since March 2023", ""]
    for market in MARKETS:
        rows = [r for r in status_rows if r["market"] == market]
        inv = [r["data_to"] for r in rows if r["status"] == "Investigate"]
        di = [r["data_to"] for r in rows if r["status"] == "Data issue"]
        rec = [r["data_to"] + (" (approved)" if "approved" in r.get("promotion_check", "") else "")
               for r in rows if "Switch recommended" in r.get("promotion_check", "") or "Switch approved" in r.get("promotion_check", "")]
        lines.append(f"- **{market}:** {len(rows)} months. Investigate: {len(inv)} ({', '.join(inv) or 'none'}). "
                     f"Data issue: {len(di)} ({', '.join(di) or 'none'}). Switch recommended: {', '.join(rec) or 'never'}.")
    (MON / f"report_{newest}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
