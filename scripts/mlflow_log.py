"""Record every backtest run in MLflow (Step 7) and register the production models (Step 9).

Everything stays on this computer: the tracking database is mlflow/mlflow.db and artifacts go in mlflow/artifacts.
MLflow's anonymous usage statistics are switched off before it is imported.

Each run = one model on one market, tested two months ahead on March 2023 to September 2026 (D19, D26, D27).
Logged per run: model name, market, training period, features, settings, MAE, RMSE, MAPE, bias, time per forecast,
the forecasts, a forecast-against-actual chart, and the model fitted on all data to the newest month.

Registry: 'Revenue Forecast Model - LV Strip' (version 1 = same month last year, alias production) and
'Revenue Forecast Model - Reno' (version 1 = same month last year, alias challenger; version 2 = Seasonal ARIMA +
game mix, alias production from the November 2026 forecast). Decisions D28, D32 to D36, D41, D45.

    .venv/bin/python scripts/mlflow_log.py

View it with:  .venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db --port 5050
"""
from __future__ import annotations

import os
os.environ["MLFLOW_DISABLE_TELEMETRY"] = "true"   # no usage statistics leave this computer
os.environ["DO_NOT_TRACK"] = "true"
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"

import csv
import math
import pickle
import tempfile
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
CLEAN, FEATURES, MODEL = ROOT / "data" / "clean", ROOT / "data" / "features", ROOT / "data" / "model"
STORE = ROOT / "mlflow"
EXPERIMENT = "Week 4 revenue forecasting: backtest, two months ahead"
EXCLUDED = {f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)}
ORDERS = [(0, 1, 0), (0, 1, 1), (1, 1, 0), (1, 1, 1)]
HORIZON = 2
CAL_FEATURES = ["days in month", "Friday and Saturday nights", "federal holidays"]
MIX_FEATURES = ["slot share of win (two months back)", "sports pool share of win (two months back)"]
TREE_FEATURES = ["last published win", "same month last year", "3-month average", "12-month average", "year-on-year change",
                 "month-on-month change", "slot share", "sports pool share", "month of year"] + CAL_FEATURES
MODELS = {  # name: (kind, inputs, description)
    "baseline same month last year": ("rule", [], "Forecast = the same month a year earlier (first-published figure)"),
    "baseline last published": ("rule", [], "Forecast = the newest published figure, two months before"),
    "ARIMA": ("arima", [], "ARIMA, order chosen by AIC each month from 4 options, d = 1"),
    "SARIMA": ("sarima", [], "Seasonal ARIMA, seasonal term (1,0,0,12), order chosen by AIC each month"),
    "SARIMA + calendar": ("sarima", ["cal"], "Seasonal ARIMA with calendar inputs for the month forecast"),
    "SARIMA + game mix": ("sarima", ["mix"], "Seasonal ARIMA with slot and sports-pool shares two months back"),
    "SARIMA + both": ("sarima", ["cal", "mix"], "Seasonal ARIMA with calendar and game-mix inputs"),
    "Random Forest": ("tree", [], "300 trees, at least 2 months per leaf, predicts log change on the same month last year"),
    "XGBoost": ("tree", [], "200 trees, depth 3, learning rate 0.05, 80% sampling, predicts log change on the same month last year"),
}


def shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    t = y * 12 + (m - 1) + n
    return f"{t // 12}-{t % 12 + 1:02d}"


class SameMonthLastYear(mlflow.pyfunc.PythonModel):
    """The production rule as an MLflow model: forecast = the first-published win for the same month a year earlier."""

    def load_context(self, context):
        h = pd.read_csv(context.artifacts["history"], dtype={"month": str})
        self.history = dict(zip(h["month"], h["win_m"]))

    def predict(self, context, model_input):
        return [self.history.get(shift(str(m), -12), float("nan")) for m in model_input["forecast_month"]]


class SeasonalArimaGameMix(mlflow.pyfunc.PythonModel):
    """Seasonal ARIMA + game mix, fitted on all data to the newest month. Forecasts the next one or two months."""

    def load_context(self, context):
        with open(context.artifacts["fitted"], "rb") as fh:
            saved = pickle.load(fh)
        self.result, self.future, self.months = saved["result"], saved["future_exog"], saved["future_months"]

    def predict(self, context, model_input):
        path = self.result.get_forecast(steps=len(self.months), exog=self.future).predicted_mean
        lookup = dict(zip(self.months, path))
        return [float(lookup.get(str(m), float("nan"))) for m in model_input["forecast_month"]]


def main() -> None:
    STORE.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{STORE / 'mlflow.db'}")
    client = MlflowClient()
    exp = client.get_experiment_by_name(EXPERIMENT)
    exp_id = exp.experiment_id if exp else client.create_experiment(EXPERIMENT, artifact_location=(STORE / "artifacts").as_uri())
    mlflow.set_experiment(experiment_id=exp_id)

    win = list(csv.DictReader(open(CLEAN / "monthly_win.csv")))
    first = {(r["month"], r["area"]): float(r["first_published"]) / 1e6 for r in win}
    months = sorted({r["month"] for r in win})
    newest = months[-1]
    games = {(r["month"], r["area"], r["game"]): float(r["win_usd"]) for r in csv.DictReader(open(CLEAN / "game_types_monthly.csv"))}
    cal = {r["month"]: r for r in csv.DictReader(open(FEATURES / "calendar.csv"))}
    results = [r for r in csv.DictReader(open(MODEL / "model_comparison.csv"))]
    results += [{**r, "order": ""} for r in csv.DictReader(open(MODEL / "tree_models_backtest.csv"))]

    def exog(t, market, use):
        row = []
        if "mix" in use:
            m = shift(t, -HORIZON); tot = games.get((m, market, "Total gaming"))
            if not tot:
                return None
            row += [games[(m, market, "Slot machines total")] / tot, games[(m, market, "Sports Pool")] / tot]
        if "cal" in use:
            c = cal[t]; row += [float(c["derived_days_in_month"]), float(c["derived_friday_saturday_nights"]), float(c["derived_federal_holidays"])]
        return row

    def fit_final(kind, use, market):
        """Fit on all data to the newest month; return (fitted object, chosen order or settings)."""
        if kind in ("arima", "sarima"):
            width = (2 if "mix" in use else 0) + (3 if "cal" in use else 0)
            ys, xs = [], []
            for m in months:
                y = np.nan if m in EXCLUDED else first[(m, market)]
                x = exog(m, market, use) if use else []
                if use and x is None:
                    y, x = np.nan, [0.0] * width
                ys.append(y); xs.append(x)
            X = np.array(xs, dtype=float) if use else None
            best = None
            for o in ORDERS:
                try:
                    if kind == "sarima":
                        r = SARIMAX(np.array(ys), exog=X, order=o, seasonal_order=(1, 0, 0, 12), enforce_stationarity=True, enforce_invertibility=True).fit(disp=False)
                    else:
                        r = ARIMA(np.array(ys), order=o).fit()
                except Exception:
                    continue
                if best is None or r.aic < best.aic:
                    best = r
            return best, str(best.model.order)
        # trees: same 12 inputs and target as scripts/tree_models.py, all clean months to the newest
        def inputs(t):
            last = shift(t, -HORIZON)
            window = [shift(t, -n) for n in range(HORIZON, 15)]
            if any(m in EXCLUDED or (m, market) not in first for m in window):
                return None
            tot = games.get((last, market, "Total gaming"))
            if not tot:
                return None
            lag = lambda n: first[(shift(t, -n), market)]
            c = cal[t]
            return [lag(2), lag(12), sum(lag(n) for n in range(2, 5)) / 3, sum(lag(n) for n in range(2, 14)) / 12,
                    lag(2) / lag(14) - 1, lag(2) / lag(3) - 1, games[(last, market, "Slot machines total")] / tot,
                    games[(last, market, "Sports Pool")] / tot, int(t[5:]), float(c["derived_days_in_month"]),
                    float(c["derived_friday_saturday_nights"]), float(c["derived_federal_holidays"])]
        X, y = [], []
        for m in months:
            if m in EXCLUDED:
                continue
            x = inputs(m)
            if x is not None:
                X.append(x); y.append(math.log(first[(m, market)] / first[(shift(m, -12), market)]))
        return (X, y), f"{len(X)} training months"

    run_ids, model_uris = {}, {}
    for market in ["LV Strip", "Reno"]:
        for name, (kind, use, description) in MODELS.items():
            rows = sorted((r for r in results if r["market"] == market and r["model"] == name), key=lambda r: r["month"])
            actual = np.array([float(r["actual_m"]) for r in rows]); fc = np.array([float(r["forecast_m"]) for r in rows])
            err = actual - fc
            with mlflow.start_run(run_name=f"{market} | {name}") as run:
                mlflow.set_tags({"market": market, "model": name, "role": "baseline" if kind == "rule" else "candidate",
                                 "decisions": "D19, D26, D27, D31"})
                features = (CAL_FEATURES if "cal" in use else []) + (MIX_FEATURES if "mix" in use else [])
                if kind == "tree":
                    features = TREE_FEATURES
                if name == "baseline same month last year":
                    features = ["first-published win 12 months before"]
                if name == "baseline last published":
                    features = ["first-published win 2 months before"]
                chosen = sorted({r.get("order", "") for r in rows if r.get("order")})
                params = {"model": name, "market": market, "description": description,
                          "training_period": "Jan 2015 to two months before each forecast; 2020-2021 left out (D23)",
                          "test_period": f"{rows[0]['month']} to {rows[-1]['month']} ({len(rows)} months)",
                          "horizon_months": HORIZON, "retraining": "every month (D39)" if kind != "rule" else "none (a rule)",
                          "features": "; ".join(features) if features else "the market's own history only",
                          "orders_chosen_by_month": ", ".join(chosen)[:450] if chosen else "n/a",
                          "timing_note": "time per forecast covers training and prediction together"}
                if kind == "sarima":
                    params["seasonal_order"] = "(1,0,0,12)"
                if name == "Random Forest":
                    params.update(n_estimators=300, min_samples_leaf=2, random_state=0)
                if name == "XGBoost":
                    params.update(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=0)
                mlflow.log_params(params)
                last12 = slice(len(rows) - 12, len(rows))
                mlflow.log_metrics({"MAE_m": float(np.mean(np.abs(err))), "RMSE_m": float(np.sqrt(np.mean(err ** 2))),
                                    "MAPE_pct": float(np.mean(np.abs(err) / actual) * 100), "bias_m": float(np.mean(err)),
                                    "MAPE_last12_pct": float(np.mean(np.abs(err[last12]) / actual[last12]) * 100),
                                    "seconds_per_forecast": float(np.mean([float(r["fit_seconds"]) for r in rows]))})
                for i, r in enumerate(rows):  # MAPE over time, one point per test month
                    mlflow.log_metric("monthly_miss_pct", float(abs(err[i]) / actual[i] * 100), step=i)
                with tempfile.TemporaryDirectory() as tmp:
                    t = Path(tmp)
                    pd.DataFrame({"month": [r["month"] for r in rows], "actual_m": actual, "forecast_m": fc,
                                  "miss_pct": err / actual * 100}).to_csv(t / "forecasts.csv", index=False)
                    fig, ax = plt.subplots(figsize=(10, 4))
                    xs = [r["month"] for r in rows]
                    ax.plot(xs, actual, label="Actual", color="#1f3b57", linewidth=2)
                    ax.plot(xs, fc, label=f"Forecast: {name}", color="#d98c1f", linewidth=1.6)
                    ax.set_xticks(xs[::3]); ax.tick_params(axis="x", rotation=45, labelsize=8)
                    ax.set_ylabel("Gaming win, $m"); ax.legend(frameon=False)
                    ax.set_title(f"{market}: {name}, two months ahead. MAPE {np.mean(np.abs(err) / actual) * 100:.1f}%")
                    ax.grid(alpha=0.25); fig.tight_layout(); fig.savefig(t / "forecast_chart.png", dpi=120); plt.close(fig)
                    mlflow.log_artifact(str(t / "forecasts.csv")); mlflow.log_artifact(str(t / "forecast_chart.png"))
                    if name == "baseline same month last year":
                        pd.DataFrame({"month": months, "win_m": [first[(m, market)] for m in months]}).to_csv(t / "history.csv", index=False)
                        info = mlflow.pyfunc.log_model(name="model", python_model=SameMonthLastYear(), artifacts={"history": str(t / "history.csv")},
                                                       input_example=pd.DataFrame({"forecast_month": [shift(newest, 2)]}))
                        model_uris[(market, name)] = info.model_uri
                    elif kind in ("arima", "sarima"):
                        fitted, order = fit_final(kind, use, market)
                        mlflow.log_param("final_model_order", order)
                        if name == "SARIMA + game mix":
                            fut_months = [shift(newest, 1), shift(newest, 2)]
                            future = np.array([exog(m, market, use) for m in fut_months], dtype=float)
                            with open(t / "fitted.pkl", "wb") as fh:
                                pickle.dump({"result": fitted, "future_exog": future, "future_months": fut_months}, fh)
                            info = mlflow.pyfunc.log_model(name="model", python_model=SeasonalArimaGameMix(), artifacts={"fitted": str(t / "fitted.pkl")},
                                                           input_example=pd.DataFrame({"forecast_month": [shift(newest, 2)]}))
                            model_uris[(market, name)] = info.model_uri
                        else:
                            with open(t / "fitted_model.pkl", "wb") as fh:
                                pickle.dump(fitted, fh)
                            mlflow.log_artifact(str(t / "fitted_model.pkl"), artifact_path="model")
                    elif kind == "tree":
                        (X, y), note = fit_final(kind, use, market)
                        model = (RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=0) if name == "Random Forest"
                                 else XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=0))
                        model.fit(np.array(X), np.array(y))
                        mlflow.log_param("final_model_training", note)
                        with open(t / "fitted_model.pkl", "wb") as fh:
                            pickle.dump(model, fh)
                        mlflow.log_artifact(str(t / "fitted_model.pkl"), artifact_path="model")
                run_ids[(market, name)] = run.info.run_id
            print(f"logged: {market} | {name}")

    # ---- Registry (Step 9) -----------------------------------------------------------------------
    def register(market, model_name, description, alias, tags):
        reg_name = f"Revenue Forecast Model - {market}"
        try:
            client.create_registered_model(reg_name, description=f"Monthly gaming-win forecast for {market}, two months ahead (D19). Production and challenger shown by alias.")
        except mlflow.exceptions.MlflowException:
            pass
        mv = mlflow.register_model(model_uris[(market, model_name)], reg_name)  # MLflow 3: models live at models:/m-..., not under the run
        client.update_model_version(reg_name, mv.version, description=description)
        for k, v in tags.items():
            client.set_model_version_tag(reg_name, mv.version, k, v)
        client.set_registered_model_alias(reg_name, alias, mv.version)
        return mv.version

    v = register("LV Strip", "baseline same month last year",
                 "V1: same month last year. Chosen for production (D28): most accurate on MAE and MAPE over 43 months, nothing to maintain.",
                 "production", {"decision": "D28", "from_forecast_month": "2023-03", "challenger": "SARIMA + both (D41), not promoted (D32)"})
    print(f"registered LV Strip version {v} as production")
    v = register("Reno", "baseline same month last year",
                 "V1: same month last year. Production until the November 2026 forecast, then the Challenger (D33).",
                 "challenger", {"decision": "D28, D33", "from_forecast_month": "2023-03", "until_forecast_month": "2026-10"})
    print(f"registered Reno version {v} as challenger")
    v = register("Reno", "SARIMA + game mix",
                 "V2: Seasonal ARIMA + game mix. Replaces V1 because it met the promotion rule (D32) at 3 monthly checks in a row from August 2026: "
                 "last-12-month MAPE 5.6% vs 6.8%, full test 7.21% vs 7.24%, lower RMSE and bias. Approved by the Product Owner (D36) once monitoring ran (D45). "
                 "Evidence: docs/week4-reno-switch-evidence-pack.md",
                 "production", {"decision": "D32, D36, D45", "from_forecast_month": "2026-11", "approved_by": "Product Owner"})
    print(f"registered Reno version {v} as production")


if __name__ == "__main__":
    main()
