# Developing FabTwin

Keep each change tied to an engineering question and a reproducible experiment. All existing data are synthetic.

```bash
python -m pip install -e '.[dev]'
python scripts/build_controller.py
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

For CMake builds, run `ctest --test-dir build -C Release --output-on-failure` to execute the native controller tests. `scripts/build_controller.py` runs them automatically.

Change the model/control code only with a corresponding behavioral test. Never tune on the held-out test or drift challenge. Preserve adverse results, metrology limitations and distinctions between physical measurements and generated data. Reference reports must be regenerated after implementation changes so source hashes remain traceable.

Use `python -m fabtwin.cli all --out runs/my-experiment --seed 7` for new work. Promote a report to `reports/reference/` only after checking plots, diagnostics and numerical results. Do not commit environments, build products, caches or credentials.

The bounded next milestones are measurement-system analysis, spatial wafer nonuniformity, multivariate detection, and the USB-only STM32 port described in `docs/STM32.md`. Firmware and physical validation are separate from host simulation.
