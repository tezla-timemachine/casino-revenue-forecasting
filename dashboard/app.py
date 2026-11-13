"""Model monitoring dashboard (Step 15). Runs on this computer only (D44).

    .venv/bin/streamlit run dashboard/app.py --server.port 8504

Reads what monitoring writes (scripts/monitor.py): data/monitoring/monthly_status.csv, forecast_log.csv,
production.json and thresholds.json, plus the full history in data/clean/monthly_win.csv.
"""
from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
MON, CLEAN = ROOT / "data" / "monitoring", ROOT / "data" / "clean"
STATUS_COLOURS = {"Healthy": "#2e7d32", "Investigate": "#e08a00", "Data issue": "#c62828"}

st.set_page_config(page_title="Revenue forecast monitoring", page_icon="📈", layout="wide")


@st.cache_data
def load():
    status = pd.read_csv(MON / "monthly_status.csv", dtype=str)
    for c in ("actual_m", "forecast_m", "mae_12m_m", "rmse_12m_m", "bias_12m_m"):
        status[c] = pd.to_numeric(status[c], errors="coerce")
    status["miss"] = pd.to_numeric(status["miss_pct"].str.rstrip("%"), errors="coerce")
    status["mape12"] = pd.to_numeric(status["mape_12m"].str.rstrip("%"), errors="coerce")
    status["date"] = pd.to_datetime(status["data_to"])
    log = pd.read_csv(MON / "forecast_log.csv", dtype=str)
    win = pd.read_csv(CLEAN / "monthly_win.csv", dtype={"month": str})
    win["date"] = pd.to_datetime(win["month"])
    win["win_m"] = win["gaming_win"].astype(float) / 1e6
    registry = json.loads((MON / "production.json").read_text())
    thresholds = json.loads((MON / "thresholds.json").read_text())
    return status, log, win, registry, thresholds


status, log, win, registry, thresholds = load()

st.sidebar.title("Revenue forecast monitoring")
market = st.sidebar.radio("Market", ["LV Strip", "Reno"])
st.sidebar.caption("Forecasts are two months ahead (D19). Data: Nevada Gaming Control Board. Runs on this computer only.")

s = status[status["market"] == market].sort_values("date")
latest = s.iloc[-1]
nxt = log[log["market"] == market]
prod_next = nxt[nxt["role"] == "production"].iloc[0]
chal_next = nxt[nxt["role"] == "challenger"].iloc[0]
th = thresholds[f"{market}|{latest['model']}"]

# ---- 15.11 health, 15.6 production model, 15.7 version --------------------------------------------
colour = STATUS_COLOURS.get(latest["status"], "#555")
st.markdown(f"## {market} &nbsp; <span style='background:{colour};color:white;padding:4px 12px;border-radius:12px;font-size:0.7em'>"
            f"{latest['status']}</span>", unsafe_allow_html=True)
st.caption(f"Latest data: {latest['date']:%B %Y}. Status rule: fast, slow and capacity alerts (D37); data check (D38).")

st.markdown(f"**In production for the next forecast:** {prod_next['model']} ({prod_next['version']}) &nbsp;·&nbsp; "
            f"**Challenger:** {chal_next['model']}")
month_label = f"{pd.to_datetime(prod_next['forecast_month']):%b %Y}"
c = st.columns(5)
c[0].metric("Production version", prod_next["version"], help="From data/monitoring/production.json; the registry is in MLflow")
c[1].metric(f"Forecast, {month_label}", f"${float(prod_next['forecast_m']):,.1f}m", help="From the production model" + (f". {prod_next['note']}" if isinstance(prod_next['note'], str) and prod_next['note'] else ""))
c[2].metric(f"Challenger forecast, {month_label}", f"${float(chal_next['forecast_m']):,.1f}m")
c[3].metric("Last retrained", prod_next["last_retrained"] if prod_next["last_retrained"] != "not applicable" else "n/a (a rule)",
            help="Models that learn settings re-learn them monthly (D39)")
c[4].metric("Data check, latest month", "Pass" if latest["data_check"] == "pass" else "Fail", help=latest["data_check"])

# ---- 15.8 latest evaluation metrics ------------------------------------------------------------
st.subheader("Latest measures (last 12 months)")
st.caption(f"For the model that made those forecasts: {latest['model']} ({latest['version']}).")
m = st.columns(4)
m[0].metric("MAPE (headline)", latest["mape_12m"], help=f"Normal for this model: {th['normal']:.1%}. Slow alert above {th['normal'] + 0.015:.1%}")
m[1].metric("MAE", f"${latest['mae_12m_m']:.1f}m")
m[2].metric("RMSE (big misses)", f"${latest['rmse_12m_m']:.1f}m")
m[3].metric("Bias", f"${latest['bias_12m_m']:+.1f}m", help="Positive = forecasts too low on average")

# ---- 15.2 actual, 15.3 forecast, 15.4 error --------------------------------------------------------
st.subheader("Actual against forecast, and the miss each month")
lines = s.melt(id_vars="date", value_vars=["actual_m", "forecast_m"], var_name="series", value_name="win")
lines["series"] = lines["series"].map({"actual_m": "Actual", "forecast_m": "Forecast"})
chart = alt.Chart(lines).mark_line(point=True).encode(
    x=alt.X("date:T", title=None), y=alt.Y("win:Q", title="Gaming win, $m", scale=alt.Scale(zero=False)),
    color=alt.Color("series:N", scale=alt.Scale(range=["#1f3b57", "#d98c1f"]), title=None),
    tooltip=[alt.Tooltip("date:T", format="%b %Y"), "series", alt.Tooltip("win:Q", format=",.1f")]).properties(height=280)
st.altair_chart(chart, use_container_width=True)
bars = alt.Chart(s).mark_bar().encode(
    x=alt.X("date:T", title=None), y=alt.Y("miss:Q", title="Miss, % of actual"),
    color=alt.condition(f"abs(datum.miss) > {th['bad_month'] * 100}", alt.value("#c62828"), alt.value("#8aa4bf")),
    tooltip=[alt.Tooltip("date:T", format="%b %Y"), alt.Tooltip("miss:Q", format="+.1f")]).properties(height=160)
st.altair_chart(bars, use_container_width=True)
st.caption(f"Red bars: a bad month, worse than {th['bad_month']:.1%} (the worst 10% for this model). Positive = actual above forecast.")

# ---- MAPE over time with the slow-alert line ----------------------------------------------------
st.subheader("12-month MAPE over time")
mape = alt.Chart(s.dropna(subset=["mape12"])).mark_line(point=True, color="#1f3b57").encode(
    x=alt.X("date:T", title=None), y=alt.Y("mape12:Q", title="12-month MAPE, %"),
    tooltip=[alt.Tooltip("date:T", format="%b %Y"), alt.Tooltip("mape12:Q", format=".2f")])
rule = alt.Chart(pd.DataFrame({"y": [(th["normal"] + 0.015) * 100]})).mark_rule(color="#e08a00", strokeDash=[6, 4]).encode(y="y:Q")
st.altair_chart((mape + rule).properties(height=220), use_container_width=True)
st.caption(f"Dashed line: slow-alert level, {th['normal'] + 0.015:.1%} (normal {th['normal']:.1%} + 1.5 points).")

# ---- 15.9 drift status --------------------------------------------------------------------------
st.subheader("Drift and alerts")
d = st.columns(3)
last12 = s.tail(12)
d[0].metric("Status this month", latest["status"])
d[1].metric("Months flagged in the last 12", int((last12["status"] != "Healthy").sum()))
d[2].metric("Promotion check", "Switch approved" if "approved" in str(latest["promotion_check"]) else
            ("Challenger passes" if "passes" in str(latest["promotion_check"]) else "Champion stays"), help=str(latest["promotion_check"]))
flagged = s[s["status"] != "Healthy"][["data_to", "status", "alerts"]].rename(columns={"data_to": "Month", "status": "Status", "alerts": "Alerts"})
st.dataframe(flagged.iloc[::-1], hide_index=True, use_container_width=True)

# ---- 15.5 historical trend ----------------------------------------------------------------------
st.subheader("Historical revenue, 2015 to now")
h = win[win["area"] == market].set_index("date")[["win_m"]]
h = h.reindex(pd.date_range(h.index.min(), h.index.max(), freq="MS")).rename_axis("date").reset_index()  # gaps stay gaps
trend = alt.Chart(h).mark_line(color="#1f3b57").encode(
    x=alt.X("date:T", title=None), y=alt.Y("win_m:Q", title="Gaming win, $m"),
    tooltip=[alt.Tooltip("date:T", format="%b %Y"), alt.Tooltip("win_m:Q", format=",.1f")]).properties(height=240)
st.altair_chart(trend, use_container_width=True)
st.caption("2020 and 2021 are not held: left out because of the COVID closures (D23).")

# ---- model history ------------------------------------------------------------------------------
with st.expander("Model history for this market"):
    st.dataframe(pd.DataFrame(registry[market]), hide_index=True, use_container_width=True)
