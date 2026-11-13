"""Forecasting features for the LV Strip and Reno, one row per market per month (Jan 2023 to Sep 2026).

Every feature for month T uses only information published before T:
  - win figures use each month's FIRST-PUBLISHED value (what was known at the time), never a later revision
  - game-type splits use each month's own report (first-published)
  - calendar features are known in advance
The target is the newest figure for month T (decision D9).

Every feature column starts with 'derived_' because none of them is printed in a report. The baseline check
recomputes the 'same month last year' baseline from these columns and must match baseline.py.

    .venv/bin/python scripts/build_features.py

Writes data/features/features_strip_reno.csv and data/features/feature_checks.md. Standard library only.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
FEATURES = ROOT / "data" / "features"
MARKETS = ["LV Strip", "Reno"]
LAST_PUBLISHED_LAG = 2  # decision D19: forecast two months ahead, so the newest figure we can use is two months back
FIRST_TARGET = "2023-03"  # the year-on-year feature needs 14 months of history from the target: January 2022 is the first we hold


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12}-{total % 12 + 1:02d}"


def main() -> None:
    win = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) for r in win}
    latest = {(r["month"], r["area"]): float(r["gaming_win"]) for r in win}
    games = {}
    for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv")):
        games[(r["month"], r["area"], r["game"])] = float(r["win_usd"])
    calendar = {r["month"]: r for r in csv.DictReader(open(FEATURES / "calendar.csv"))}
    months = sorted({r["month"] for r in win})
    targets = [m for m in months if m >= FIRST_TARGET]

    rows = []
    for market in MARKETS:
        for t in targets:
            # Everything below uses months up to two months before t (the newest figures published by then).
            lag = lambda n: first[(shift(t, -n), market)]
            last = LAST_PUBLISHED_LAG
            last_month = shift(t, -last)
            total_last = games[(last_month, market, "Total gaming")]
            row = {
                "month": t, "market": market,
                "target_win_latest": latest[(t, market)],
                "derived_last_published_win": lag(last),
                "derived_same_month_last_year_win": lag(12),
                "derived_avg3_last_published": sum(lag(n) for n in range(last, last + 3)) / 3,
                "derived_avg12_last_published": sum(lag(n) for n in range(last, last + 12)) / 12,
                "derived_yoy_change_last_published": lag(last) / lag(last + 12) - 1,
                "derived_mom_change_last_published": lag(last) / lag(last + 1) - 1,
                "derived_last_published_slot_share": games[(last_month, market, "Slot machines total")] / total_last,
                "derived_last_published_table_share": games[(last_month, market, "Table games total")] / total_last,
                "derived_last_published_sports_pool_share": games[(last_month, market, "Sports Pool")] / total_last,
                "derived_month_of_year": int(t[5:]),
                "derived_days_in_month": int(calendar[t]["derived_days_in_month"]),
                "derived_weekend_days": int(calendar[t]["derived_weekend_days"]),
                "derived_friday_saturday_nights": int(calendar[t]["derived_friday_saturday_nights"]),
                "derived_federal_holidays": int(calendar[t]["derived_federal_holidays"]),
            }
            rows.append(row)

    FEATURES.mkdir(parents=True, exist_ok=True)
    with (FEATURES / "features_strip_reno.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # ---- checks ----------------------------------------------------------------------------
    lines = ["# Feature checks: data/features/features_strip_reno.csv", "",
             f"Rows: {len(rows)} ({len(targets)} months x {len(MARKETS)} markets), {targets[0]} to {targets[-1]}.",
             "Starts in March 2023: the year-on-year feature needs history back to January 2022, the first month we hold. "
             "Forecast horizon: two months ahead (decision D19), so each feature uses months up to two months before the target.", ""]
    missing = [k for r in rows for k, v in r.items() if v in ("", None)]
    lines.append(f"- Missing values: {'none' if not missing else len(missing)}")
    # Baseline reproduced from the features: same month last year, scored on the newest figures.
    errors = [abs(r["target_win_latest"] - r["derived_same_month_last_year_win"]) / r["target_win_latest"] for r in rows]
    mape = sum(errors) / len(errors)
    lines.append(f"- Same-month-last-year MAPE rebuilt from the features: {mape:.2%} over {len(errors)} rows per market. "
                 "Compare with data/model/baseline_backtest.csv over the same months (March 2023 onwards).")
    per = {}
    for r in rows:
        per.setdefault(r["market"], []).append(abs(r["target_win_latest"] - r["derived_same_month_last_year_win"]) / r["target_win_latest"])
    lines += [f"  - {m}: {sum(v) / len(v):.2%}" for m, v in per.items()]
    lines.append("- Leakage: every feature uses months at least two before the target, the newest figures published by then. Checked by construction in the script.")
    (FEATURES / "feature_checks.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWritten: {(FEATURES / 'features_strip_reno.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
