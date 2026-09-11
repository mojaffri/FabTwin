"""Verify saved experiment evidence without rerunning or fitting to test data."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fabtwin.simulation import FEATURES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("reports/reference"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((args.directory / "manifest.json").read_text())
    for name, digest in manifest["source_sha256"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, (
            f"Source changed: {name}"
        )
    design = pd.read_csv(args.directory / "doe/design.csv")
    confirmations = pd.read_csv(args.directory / "doe/confirmation.csv")
    assert len(design) == 40 and len(confirmations) == 12
    assert set(design.seed).isdisjoint(confirmations.seed)
    t, p, f = design[["T", "P", "F"]].to_numpy().T
    matrix = np.column_stack([np.ones(40), t, p, f, t * p, t * f, p * f, t * t, p * p, f * f])
    assert np.linalg.matrix_rank(matrix) == 10
    vm = pd.read_csv(args.directory / "vm/wafers.csv")
    metrics = json.loads((args.directory / "vm/metrics.json").read_text())
    assert vm.seed.is_unique and vm.wafer.is_monotonic_increasing
    assert metrics["features"] == FEATURES
    assert vm.split.drop_duplicates().tolist() == ["train", "tune", "calibration", "test", "drift"]
    for split in ["test", "drift"]:
        block = vm.loc[vm.split == split]
        mae = abs(block.measured_thickness_nm - block.predicted_nm).mean()
        assert np.isclose(mae, metrics["evaluation"][split]["MAE_nm"])
    cal = vm.loc[vm.split == "calibration"]
    errors = np.sort(abs(cal.measured_thickness_nm - cal.predicted_nm))
    assert np.isclose(
        errors[int(np.ceil((len(errors) + 1) * 0.9)) - 1], metrics["interval_half_width_nm"]
    )
    print(
        "PASS: source hashes, DOE rank, confirmation separation, VM splits, calibration and reported MAE"
    )


if __name__ == "__main__":
    main()
