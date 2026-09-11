import argparse
import hashlib
import importlib.metadata
import platform
from datetime import datetime, timezone
from pathlib import Path

from .experiments import doe, faults, metrology, save_json, spc
from .model import Recipe
from .plots import cycle, doe_fig, spc_fig, vm_fig
from .simulation import simulate


def main():
    parser = argparse.ArgumentParser(
        description="FabTwin: synthetic deposition and manufacturing analytics"
    )
    parser.add_argument("experiment", choices=["demo", "doe", "spc", "vm", "faults", "all"])
    parser.add_argument("--out", type=Path, default=Path("runs/latest"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.seed < 0:
        parser.error("--seed must be nonnegative")
    args.out.mkdir(parents=True, exist_ok=True)
    recipe = Recipe()
    metrics = {}
    if args.experiment in ["demo", "all"]:
        run = simulate(seed=args.seed)
        run.trace.to_csv(args.out / "cycle.csv", index=False)
        save_json(args.out / "cycle_summary.json", run.summary)
        cycle(run.trace, args.out / "cycle.png")
        metrics["cycle"] = run.summary
        print(
            f"Cycle: {run.summary['state']}, {run.summary['measured_thickness_nm']:.2f} nm",
            flush=True,
        )
    if args.experiment in ["doe", "all"]:
        print("Running 40 DOE wafers + 12 independent confirmations...", flush=True)
        data, grid, residual, m, recipe = doe(args.out / "doe", args.seed + 34)
        doe_fig(data, grid, residual, args.out / "doe.png")
        metrics["doe"] = m
    if args.experiment in ["spc", "all"]:
        data, chart, m = spc(args.out / "spc", recipe, args.seed + 44)
        spc_fig(data, chart, m, args.out / "spc.png")
        metrics["spc"] = m
    if args.experiment in ["vm", "all"]:
        data, m = metrology(args.out / "vm", args.seed + 54)
        vm_fig(data, m, args.out / "vm.png")
        metrics["vm"] = m
    if args.experiment in ["faults", "all"]:
        matrix = faults(args.out / "faults")
        metrics["faults"] = matrix[["injection", "state", "fault", "cycle_s"]].to_dict("records")
    root = Path(__file__).resolve().parents[2]
    files = (
        list((root / "src").rglob("*.py"))
        + list((root / "controller").rglob("*.cpp"))
        + list((root / "controller").rglob("*.hpp"))
    )
    manifest = dict(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        seed=args.seed,
        python=platform.python_version(),
        platform=platform.platform(),
        versions={
            name: importlib.metadata.version(name)
            for name in ["numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "matplotlib"]
        },
        source_sha256={
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files)
        },
        simulation_only=True,
        controller="Compiled C++17 host library; CRC-framed in-memory serial emulation",
    )
    from .protocol import Controller

    with Controller() as controller:
        library = Path(controller.lib._name)
        manifest["controller_binary_sha256"] = hashlib.sha256(library.read_bytes()).hexdigest()
        manifest["controller_binary_name"] = library.name
    save_json(args.out / "manifest.json", manifest)
    save_json(args.out / "metrics.json", metrics)
    lines = [
        "# FabTwin experiment report",
        "",
        "All results are synthetic. Controller executes on the host computer; no physical hardware testing.",
        "",
    ]
    if "doe" in metrics:
        m = metrics["doe"]
        lines += [
            f"DOE: {m['runs']} runs + {m['confirmation_n']} independent confirmation wafers. Confirmation thickness: {m['confirmation_mean_nm']:.2f} ± {m['confirmation_std_nm']:.2f} nm (sample SD).",
            "",
            "![DOE](doe.png)",
            "",
        ]
    if "spc" in metrics:
        m = metrics["spc"]
        c = m["baseline_capability"]
        lines += [
            f"SPC: baseline Cp {c['Cp']:.2f}, Cpk {c['Cpk']:.2f}; descriptive estimates, subject to Phase I diagnostics. EWMA first post-drift signal: wafer {m['first_ewma_detection_wafer']}; delay {m['detection_delay_wafers']} wafers. Pre-drift signals: {m['pre_drift_ewma_alarm_count']}/{m['pre_drift_monitoring_wafers']} monitored wafers.",
            "",
            "![SPC](spc.png)",
            "",
        ]
        lines += [
            f"Phase I contains {m['phase1']['phase1_individual_signals']} individual-chart and {m['phase1']['phase1_mr_signals']} moving-range signals. These are retained. The baseline has not been qualified as statistically in control; capability values are descriptive estimates, not process acceptance evidence.",
            "",
        ]
    if "vm" in metrics:
        m = metrics["vm"]
        lines += [
            f"VM: selected {m['selected_model']}; held-out MAE {m['evaluation']['test']['MAE_nm']:.2f} nm, drift MAE {m['evaluation']['drift']['MAE_nm']:.2f} nm. Held-out interval coverage {m['evaluation']['test']['interval_coverage']:.0%}; drift coverage {m['evaluation']['drift']['interval_coverage']:.0%}.",
            "",
            "![VM](vm.png)",
            "",
        ]
        test = m["evaluation"]["test"]
        interval = test["MAE_bootstrap_95_interval_nm"]
        detector = m["residual_monitor"]
        lines += [
            "| Held-out benchmark | MAE / nm |",
            "|---|---:|",
            f"| Training-mean predictor | {test['mean_baseline_MAE_nm']:.2f} |",
            f"| Nominal kinetics from measured traces | {test['nominal_kinetics_MAE_nm']:.2f} |",
            f"| Selected virtual-metrology model | {test['MAE_nm']:.2f} |",
            "",
            f"VM MAE bootstrap 95% interval: {interval[0]:.2f}–{interval[1]:.2f} nm, assuming independent test wafers. The kinetics baseline deliberately shares the simulator's nominal structure and coefficients; it has no access to true wafer gain. It is a strong synthetic benchmark, not independently validated chemistry.",
            "",
            f"Delayed-metrology residual EWMA first signals at wafer {detector['first_signal_wafer']} after drift starts at wafer 261 (delay {detector['delay_wafers']} wafers). Pre-drift flags: {detector['pre_drift_alarm_count']}/40. Limits are frozen from calibration residuals; this detector requires measured thickness and cannot independently discover drift before metrology arrives.",
            "",
        ]
    lines += [
        "Full metrics, raw wafer records, design tables, diagnostics and source hashes accompany this report.",
        "",
    ]
    (args.out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("Results:", args.out.resolve(), flush=True)


if __name__ == "__main__":
    main()
