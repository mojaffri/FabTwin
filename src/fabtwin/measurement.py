"""Balanced crossed random-effects Gage R&R for a synthetic thickness measurement study."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def analyze(data, tolerance_nm=10.0):
    required = {"part", "operator", "repeat", "thickness_nm"}
    if not required.issubset(data) or not np.isfinite(data.thickness_nm).all():
        raise ValueError("Missing or nonfinite measurement data")
    if data.duplicated(["part", "operator", "repeat"]).any():
        raise ValueError("Duplicate measurements")
    cube = data.pivot(index=["part", "operator"], columns="repeat", values="thickness_nm")
    p, o, r = data.part.nunique(), data.operator.nunique(), data.repeat.nunique()
    if min(p, o, r) < 2 or len(data) != p * o * r or cube.isna().any().any():
        raise ValueError("Need a complete balanced crossed study with >=2 levels per factor")
    if not np.isfinite(tolerance_nm) or tolerance_nm <= 0:
        raise ValueError("Tolerance width must be positive")
    grand = data.thickness_nm.mean()
    part = data.groupby("part").thickness_nm.mean()
    operator = data.groupby("operator").thickness_nm.mean()
    cells = data.groupby(["part", "operator"]).thickness_nm.mean()
    ms_part = o * r * ((part - grand) ** 2).sum() / (p - 1)
    ms_operator = p * r * ((operator - grand) ** 2).sum() / (o - 1)
    interaction_ss = r * sum(
        (v - part[a] - operator[b] + grand) ** 2 for (a, b), v in cells.items()
    )
    ms_interaction = interaction_ss / ((p - 1) * (o - 1))
    residual_ss = sum(
        (row.thickness_nm - cells[row.part, row.operator]) ** 2 for row in data.itertuples()
    )
    ms_repeat = residual_ss / (p * o * (r - 1))
    variances = dict(
        repeatability=float(ms_repeat),
        operator=max(0.0, float((ms_operator - ms_interaction) / (p * r))),
        interaction=max(0.0, float((ms_interaction - ms_repeat) / r)),
        part=max(0.0, float((ms_part - ms_interaction) / (o * r))),
    )
    grr = sum(variances[k] for k in ["repeatability", "operator", "interaction"])
    if sum(variances.values()) <= 0:
        raise ValueError("Study variation is zero; relative measurement variation is undefined")
    return dict(
        n=len(data),
        variance_components_nm2=variances,
        grr_sigma_nm=float(np.sqrt(grr)),
        percent_tolerance=100 * 6 * float(np.sqrt(grr)) / tolerance_nm,
        percent_study_variation=100 * float(np.sqrt(grr / sum(variances.values()))),
        note="Unpooled crossed random-effects ANOVA; negative variance estimates truncated at zero. Synthetic only.",
    )


def study(seed=7, repeat_sigma=0.2, operator_sigma=0.15):
    if (
        min(repeat_sigma, operator_sigma) < 0
        or not np.isfinite([repeat_sigma, operator_sigma]).all()
    ):
        raise ValueError("Noise scales must be finite and nonnegative")
    rng = np.random.default_rng(seed)
    parts, operators = rng.normal(100, 1.5, 10), rng.normal(0, operator_sigma, 3)
    interaction = rng.normal(0, 0.05, (10, 3))
    rows = [
        dict(
            part=p,
            operator=o,
            repeat=r,
            thickness_nm=parts[p] + operators[o] + interaction[p, o] + rng.normal(0, repeat_sigma),
        )
        for p in range(10)
        for o in range(3)
        for r in range(3)
    ]
    rng.shuffle(rows)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("runs/measurement"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, sigma in [("nominal", 0.2), ("noisy_gage", 1.0)]:
        data = study(args.seed, repeat_sigma=sigma)
        data.to_csv(args.out / f"{name}.csv", index=False)
        results[name] = analyze(data)
    (args.out / "metrics.json").write_text(
        json.dumps(results, indent=2, allow_nan=False), encoding="utf-8"
    )
    manifest = dict(
        seed=args.seed,
        simulation_only=True,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        data_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.out.glob("*.csv"))
        },
    )
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
