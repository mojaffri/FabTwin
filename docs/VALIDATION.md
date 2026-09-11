# First-release validation

Reference environment: Windows 11 x86-64, Python 3.12.14, Zig 0.16.0 C++ compiler, C++17 optimized host build. Exact Python package versions and source / controller binary hashes are recorded in `reports/reference/manifest.json`. The compiler successfully built the host DLL. Initial Zig standard-library compilation emitted upstream nullability warnings; the final incremental controller build completed without diagnostics.

## Completed locally

- 37 pytest tests passed against the compiled controller, plus native C++ checks for PID anti-windup/recovery, stability dwell, process-window debounce and active-reset rejection.
- Full 620-cycle workflow: one nominal cycle, 40 DOE wafers, 12 independent confirmation wafers, 260 SPC wafers, 300 VM wafers, seven fault scenarios.
- Report verification checks source hashes, full-rank quadratic DOE, disjoint confirmation seeds, unique VM wafer seeds, chronological split order, recalculated held-out/drift MAE, and interval calibration order statistic.
- The saved virtual-metrology model was loaded and used by the prediction example.
- Python package wheel build succeeded; documented usage is an editable repository install with a separately built controller.
- Cycle, DOE, SPC and virtual-metrology figures were visually inspected for readable labels and consistent results.

## Test coverage

Tests exercise nominal state order, deposition duration, temperature/pressure regulation, actuator bounds, nondecreasing film thickness, precursor gating, five injected shutdown cases, nonfinite sensors, overtemperature/pressure, latched faults and explicit safe reset, malformed packets / CRC / trailing fields / oversize frames, duplicate sequence, recipe bounds, communication silence, sequence resynchronization, deterministic replay, a timestep convergence comparison, and plausible undetected sensor bias.

Statistical tests independently check MR-based capability versus overall variation, the EWMA recurrence and frozen limits, invalid inputs, and exclusion of truth/label features.

## Not yet validated

The supplied GitHub Actions Windows/Linux workflow has not been remotely executed. No Linux/macOS build was run locally, no target MCU was compiled/flashed, no UART hardware was exercised, and no real process data were collected. Tests support this host simulation implementation; they are not industrial controller certification or physical model validation.

## Reproduction

```bash
python scripts/build_controller.py
python -m pytest -q
python -m fabtwin.cli all --out runs/reproduction --seed 7
python scripts/verify_report.py runs/reproduction
python examples/predict_thickness.py --model runs/reproduction/vm/model.joblib --wafers runs/reproduction/vm/wafers.csv
```

The report verifier intentionally rejects a saved report if its recorded implementation source differs from the current source. Regenerate the report after changing the model or controller. It does not require binary hashes to match across platforms; different toolchains legitimately produce different binaries.
