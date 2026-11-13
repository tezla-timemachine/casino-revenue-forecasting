"""Charts for the exploratory analysis (docs/week4-exploratory-analysis.md). Writes PNGs to docs/charts/.

    .venv/bin/python scripts/eda_charts.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "charts"
COLOURS = {"LV Strip": "#1f3b57", "Downtown": "#d98c1f", "Reno": "#2e7d32", "Laughlin": "#8e44ad"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    w = pd.read_csv(ROOT / "data/clean/monthly_win.csv", dtype={"month": str})
    w["win"], w["y"], w["m"] = w["gaming_win"] / 1e6, w["month"].str[:4], w["month"].str[5:].astype(int)
    years = ["2015", "2016", "2017", "2018", "2019", "2022", "2023", "2024", "2025"]

    # 1. Annual win, indexed to 2015 = 100
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for area, col in COLOURS.items():
        yr = w[(w.area == area) & w.y.isin(years)].groupby("y").win.sum()
        idx = yr / yr["2015"] * 100
        x = [int(y) for y in idx.index]
        ax.plot(x[:5], idx.values[:5], color=col, marker="o", label=area)
        ax.plot(x[5:], idx.values[5:], color=col, marker="o")
    ax.axvspan(2019.5, 2021.5, color="#ddd", alpha=0.6); ax.text(2020.5, 102, "2020-21\nleft out", ha="center", fontsize=8, color="#555")
    ax.axhline(100, color="#999", lw=0.8, ls=":")
    ax.set_title("Annual gaming win, indexed (2015 = 100)"); ax.set_ylabel("Index"); ax.legend(frameon=False, ncol=4, fontsize=8)
    ax.grid(alpha=0.25); fig.tight_layout(); fig.savefig(OUT / "1_annual_win_indexed.png", dpi=130); plt.close(fig)

    # 2. Seasonal pattern before and after COVID
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, area in zip(axes, ["LV Strip", "Reno"]):
        for label, yrs, style in [("2015-19", years[:5], "--"), ("2022-25", years[5:], "-")]:
            d = w[(w.area == area) & w.y.isin(yrs)]
            idx = (d.win / d.groupby("y").win.transform("mean")).groupby(d.m).mean()
            ax.plot(MONTHS, idx.values, ls=style, marker="o", color=COLOURS[area], label=label)
        ax.axhline(1, color="#999", lw=0.8, ls=":"); ax.set_title(area); ax.grid(alpha=0.25); ax.legend(frameon=False, fontsize=8)
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel("Month as share of its year's average")
    fig.suptitle("Seasonal pattern: before and after COVID"); fig.tight_layout(); fig.savefig(OUT / "2_seasonal_pattern.png", dpi=130); plt.close(fig)

    # 3. Strip: fewer slot machines, more win per machine
    c = pd.read_csv(ROOT / "data/clean/capacity_hold_monthly.csv", dtype={"month": str})
    s = c[c.area == "LV Strip"].copy(); s["date"] = pd.to_datetime(s.month)
    s = s.set_index("date").reindex(pd.date_range(s.date.min(), s.date.max(), freq="MS"))
    fig, ax = plt.subplots(figsize=(9, 4)); ax2 = ax.twinx()
    ax.plot(s.index, s.slot_units / 1000, color="#1f3b57", label="Slot machines (thousands)")
    ax2.plot(s.index, s.slot_win_k / s.slot_units, color="#d98c1f", label="Slot win per machine ($k a month)")
    ax.set_ylabel("Slot machines, thousands", color="#1f3b57"); ax2.set_ylabel("Win per machine, $k a month", color="#d98c1f")
    ax.set_title("LV Strip: fewer slot machines, each earning more"); ax.grid(alpha=0.25)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 0.9), ncol=2, frameon=False, fontsize=8); fig.tight_layout()
    fig.savefig(OUT / "3_strip_capacity.png", dpi=130); plt.close(fig)

    # 4. Strip: forecast miss against the change in baccarat hold
    mc = pd.read_csv(ROOT / "data/model/model_comparison.csv", dtype={"month": str})
    b = mc[(mc.market == "LV Strip") & (mc.model == "baseline same month last year")].set_index("month")
    miss = (b.actual_m - b.forecast_m) / b.actual_m * 100
    st = c[c.area == "LV Strip"].set_index("month").baccarat_hold_pct.astype(float)
    dh = (st - st.shift(12)).reindex(miss.index)
    r = miss.corr(dh)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.scatter(dh, miss, color="#1f3b57", alpha=0.75)
    k, c0 = np.polyfit(dh, miss, 1); xs = np.linspace(dh.min(), dh.max(), 10); ax.plot(xs, k * xs + c0, color="#d98c1f")
    ax.axhline(0, color="#999", lw=0.8); ax.axvline(0, color="#999", lw=0.8)
    ax.set_xlabel("Baccarat hold this month minus same month last year (points)")
    ax.set_ylabel("Forecast miss, % (+ = actual above forecast)")
    ax.set_title(f"LV Strip: misses follow baccarat luck (correlation {r:.2f}, 43 months)", fontsize=10)
    ax.grid(alpha=0.25); fig.tight_layout(); fig.savefig(OUT / "4_strip_miss_vs_hold.png", dpi=130); plt.close(fig)
    print("charts written to", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
