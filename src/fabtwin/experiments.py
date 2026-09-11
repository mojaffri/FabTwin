"""Reproducible experiments: all wafer outcomes pass through the C++ controller."""

import itertools
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from statsmodels.stats.anova import anova_lm

from .model import Disturbance, Recipe
from .simulation import FEATURES, simulate
from .statistics import capability, monitor


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def completed(recipe, seed, **kwargs):
    run = simulate(recipe, seed, **kwargs)
    if run.summary["state"] != "COMPLETE":
        raise RuntimeError(f"Experiment wafer aborted: {run.summary}")
    return run


def doe(directory, seed=41):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    factorial = list(itertools.product([-1.0, 1.0], repeat=3))
    axial = [
        tuple(sign if j == axis else 0.0 for j in range(3))
        for axis in range(3)
        for sign in [-1.0, 1.0]
    ]
    design = (factorial + axial + [(0.0, 0.0, 0.0)] * 6) * 2
    rng.shuffle(design)
    rows = []
    for i, (t, p, f) in enumerate(design):
        row = completed(Recipe(450 + 15 * t, 3 + 0.4 * p, 100 + 15 * f), seed * 1000 + i).summary
        rows.append(dict(run_order=i + 1, T=t, P=p, F=f, **row))
    data = pd.DataFrame(rows)
    formula = "measured_thickness_nm ~ T + P + F + T:P + T:F + P:F + I(T**2) + I(P**2) + I(F**2)"
    model = smf.ols(formula, data=data).fit()
    anova = anova_lm(model, typ=2)
    group = data.groupby(["T", "P", "F"]).measured_thickness_nm
    pure_ss = float(group.apply(lambda g: ((g - g.mean()) ** 2).sum()).sum())
    pure_df = len(data) - group.ngroups
    lof_df = int(model.df_resid) - pure_df
    lof_ss = max(0, float(model.ssr) - pure_ss)
    lof_f = (lof_ss / lof_df) / (pure_ss / pure_df)
    grid = pd.DataFrame(
        itertools.product(np.linspace(-1, 1, 21), repeat=3), columns=["T", "P", "F"]
    )
    grid["predicted_nm"] = model.predict(grid)
    grid["target_error_nm"] = abs(grid.predicted_nm - 100)
    # Target matching is a defined objective, not a claim of global optimization.
    best = grid.loc[grid.target_error_nm.idxmin()]
    recipe = Recipe(450 + 15 * best["T"], 3 + 0.4 * best["P"], 100 + 15 * best["F"])
    confirmations = pd.DataFrame(
        [completed(recipe, seed * 1000 + 100 + i).summary for i in range(12)]
    )
    residual = pd.DataFrame(
        dict(fitted=model.fittedvalues, residual=model.resid, run_order=data.run_order)
    )
    metrics = dict(
        design="Replicated face-centered central composite: 16 factorial, 12 axial, 12 center runs; randomized order",
        runs=len(data),
        model_rank=int(model.model.rank),
        residual_df=int(model.df_resid),
        r_squared=float(model.rsquared),
        lack_of_fit=dict(
            F=lof_f, p=float(stats.f.sf(lof_f, lof_df, pure_df)), df=lof_df, pure_error_df=pure_df
        ),
        recipe=asdict(recipe),
        predicted_thickness_nm=float(best.predicted_nm),
        confirmation_mean_nm=float(confirmations.measured_thickness_nm.mean()),
        confirmation_std_nm=float(confirmations.measured_thickness_nm.std()),
        confirmation_n=12,
        note="Local quadratic approximation; synthetic effects and p-values do not establish physical process validity.",
    )
    data.to_csv(directory / "design.csv", index=False)
    anova.to_csv(directory / "anova.csv")
    grid.to_csv(directory / "process_window.csv", index=False)
    confirmations.to_csv(directory / "confirmation.csv", index=False)
    residual.to_csv(directory / "residuals.csv", index=False)
    (directory / "regression.txt").write_text(model.summary().as_text(), encoding="utf-8")
    save_json(directory / "metrics.json", metrics)
    return data, grid, residual, metrics, recipe


def spc(directory, recipe, seed=51, wafers=260, baseline=80, drift_start=160):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(wafers):
        # Persistent unmeasured chamber surface change, independent wafer noise.
        gain = 1 + max(0, i - drift_start + 1) * 0.0015
        row = completed(recipe, seed * 1000 + i, surface_gain=gain).summary
        rows.append(dict(wafer=i + 1, surface_gain=gain, **row))
        if (i + 1) % 50 == 0:
            print(f"SPC: {i + 1}/{wafers} simulated wafers", flush=True)
    data = pd.DataFrame(rows)
    reference = data.measured_thickness_nm.iloc[:baseline]
    chart, diagnostics = monitor(reference, data.measured_thickness_nm.iloc[baseline:])
    chart["wafer"] = data.wafer.iloc[baseline:].to_numpy()
    signals = chart.loc[(chart.wafer > drift_start) & chart.ewma_alarm, "wafer"]
    metrics = dict(
        baseline_wafers=baseline,
        drift_first_wafer=drift_start + 1,
        first_ewma_detection_wafer=None if signals.empty else int(signals.iloc[0]),
        detection_delay_wafers=None if signals.empty else int(signals.iloc[0] - (drift_start + 1)),
        pre_drift_ewma_alarm_count=int(chart.loc[chart.wafer <= drift_start, "ewma_alarm"].sum()),
        pre_drift_monitoring_wafers=drift_start - baseline,
        baseline_capability=capability(reference),
        phase1=diagnostics,
        note="Limits frozen after baseline. Post-drift capability deliberately not reported; chart uses delayed simulated metrology at one measurement per wafer.",
    )
    data.to_csv(directory / "wafers.csv", index=False)
    chart.to_csv(directory / "charts.csv", index=False)
    save_json(directory / "metrics.json", metrics)
    return data, chart, metrics


def score(y, pred):
    return dict(
        MAE_nm=float(mean_absolute_error(y, pred)),
        RMSE_nm=float(np.sqrt(mean_squared_error(y, pred))),
        R2=float(r2_score(y, pred)),
    )


def nominal_kinetics_prediction(data):
    """Fixed model-structure baseline using measured traces, no hidden wafer gain.

    Coefficients deliberately match the nominal simulator, giving this baseline a
    structural advantage. It is a benchmark, not independently validated physics.
    """
    return (
        0.83
        * data.thermal_dose
        * (data.pressure_mean / (data.pressure_mean + 1) / 0.75)
        * (data.flow_mean / (data.flow_mean + 50) / (2 / 3))
    )


def bootstrap_mae_interval(actual, predicted, seed=83, repetitions=2000):
    """Percentile interval under independent-wafer resampling, not drift inference."""
    errors = np.abs(np.asarray(actual) - np.asarray(predicted))
    if errors.ndim != 1 or len(errors) < 2 or not np.isfinite(errors).all():
        raise ValueError("At least two finite paired observations are required")
    rng = np.random.default_rng(seed)
    samples = errors[rng.integers(0, len(errors), size=(repetitions, len(errors)))].mean(axis=1)
    return np.quantile(samples, [0.025, 0.975]).tolist()


def metrology(directory, seed=61):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(300):
        recipe = Recipe(
            rng.uniform(435, 465),
            rng.uniform(2.6, 3.4),
            rng.uniform(85, 115),
            rng.uniform(110, 130),
        )
        split = (
            "train"
            if i < 140
            else "tune"
            if i < 180
            else "calibration"
            if i < 220
            else "test"
            if i < 260
            else "drift"
        )
        gain = 1 + max(0, i - 259) * 0.002
        rows.append(
            dict(
                wafer=i + 1,
                split=split,
                **completed(recipe, seed * 1000 + i, surface_gain=gain).summary,
            )
        )
        if (i + 1) % 50 == 0:
            print(f"VM: {i + 1}/300 simulated wafers", flush=True)
    data = pd.DataFrame(rows)
    sets = {
        name: data.loc[data.split == name]
        for name in ["train", "tune", "calibration", "test", "drift"]
    }
    train, tune = sets["train"], sets["tune"]
    candidates = {
        f"quadratic_ridge_{a}": make_pipeline(
            StandardScaler(), PolynomialFeatures(2, include_bias=False), Ridge(alpha=a)
        )
        for a in [0.1, 1.0, 10.0]
    }
    candidates["random_forest"] = RandomForestRegressor(
        n_estimators=200, max_depth=8, min_samples_leaf=3, random_state=seed, n_jobs=1
    )
    validation = {}
    for name, model in candidates.items():
        model.fit(train[FEATURES], train.measured_thickness_nm)
        validation[name] = score(tune.measured_thickness_nm, model.predict(tune[FEATURES]))[
            "MAE_nm"
        ]
    chosen = min(validation, key=validation.get)
    model = candidates[chosen]
    # No refit after selection; separate untouched calibration set.
    cal = sets["calibration"]
    errors = np.abs(cal.measured_thickness_nm - model.predict(cal[FEATURES]))
    rank = min(len(errors), int(np.ceil((len(errors) + 1) * 0.90)))
    radius = float(np.sort(errors)[rank - 1])
    data["predicted_nm"] = model.predict(data[FEATURES])
    data["lower_nm"] = data.predicted_nm - radius
    data["upper_nm"] = data.predicted_nm + radius
    data["nominal_kinetics_nm"] = nominal_kinetics_prediction(data)
    metrics = dict(
        features=FEATURES,
        split_sizes={k: len(v) for k, v in sets.items()},
        selected_model=chosen,
        tuning_MAE_nm=validation,
        interval_half_width_nm=radius,
        nominal_coverage=0.9,
        evaluation={},
        note="Chronological disjoint wafer splits. Synthetic data only. Marginal conformal interpretation requires exchangeability; drift violates it. No physical accuracy claim.",
    )
    mean = float(train.measured_thickness_nm.mean())
    for split in ["test", "drift"]:
        block = data.loc[data.split == split]
        metrics["evaluation"][split] = dict(
            **score(block.measured_thickness_nm, block.predicted_nm),
            mean_baseline_MAE_nm=float(np.abs(block.measured_thickness_nm - mean).mean()),
            nominal_kinetics_MAE_nm=float(
                np.abs(block.measured_thickness_nm - block.nominal_kinetics_nm).mean()
            ),
            interval_coverage=float(
                (abs(block.measured_thickness_nm - block.predicted_nm) <= radius).mean()
            ),
        )
    test = data.loc[data.split == "test"]
    metrics["evaluation"]["test"]["MAE_bootstrap_95_interval_nm"] = bootstrap_mae_interval(
        test.measured_thickness_nm, test.predicted_nm, seed
    )
    reference_residuals = cal.measured_thickness_nm - model.predict(cal[FEATURES])
    future = data.loc[data.split.isin(["test", "drift"])]
    residual_chart, diagnostics = monitor(
        reference_residuals, future.measured_thickness_nm - future.predicted_nm
    )
    residual_chart["wafer"] = future.wafer.to_numpy()
    signals = residual_chart.loc[(residual_chart.wafer >= 261) & residual_chart.ewma_alarm, "wafer"]
    metrics["residual_monitor"] = dict(
        first_drift_wafer=261,
        first_signal_wafer=None if signals.empty else int(signals.iloc[0]),
        delay_wafers=None if signals.empty else int(signals.iloc[0] - 261),
        pre_drift_alarm_count=int(
            residual_chart.loc[residual_chart.wafer < 261, "ewma_alarm"].sum()
        ),
        pre_drift_wafers=40,
        calibration_diagnostics=diagnostics,
        note="Uses delayed simulated metrology, not real-time fault discovery. Limits frozen from the independent calibration split.",
    )
    residual_chart.to_csv(directory / "residual_monitor.csv", index=False)
    import joblib

    joblib.dump(
        dict(model=model, features=FEATURES, interval_half_width_nm=radius),
        directory / "model.joblib",
    )
    data.to_csv(directory / "wafers.csv", index=False)
    save_json(directory / "metrics.json", metrics)
    return data, metrics


def faults(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cases = [
        Disturbance("door_open", 150),
        Disturbance("estop", 150),
        Disturbance("stale", 150),
        Disturbance("vacuum_leak", 150, 10),
        Disturbance("heater_loss", 40, 0.8),
        Disturbance("sensor_bias", 150, 8),
        Disturbance("heater_loss", 150, 0.8),
    ]
    rows = []
    for case in cases:
        run = simulate(disturbance=case)
        label = (
            "deposition_heater_loss"
            if case.kind == "heater_loss" and case.onset_s == 150
            else case.kind
        )
        run.trace.to_csv(directory / (label + ".csv"), index=False)
        rows.append(dict(injection=label, onset_s=case.onset_s, **run.summary))
    data = pd.DataFrame(rows)
    data.to_csv(directory / "fault_matrix.csv", index=False)
    return data
