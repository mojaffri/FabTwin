# Resume and interview material

Use these claims after running the project yourself and understanding the code, assumptions, results and tests. This initial implementation was created with AI assistance; describe your own contributions accurately as you extend it. Do not present code you cannot explain as independent experimental work.

## Resume entry

**FabTwin — Semiconductor Process Control & Virtual Metrology Simulator**
Python, C++17, DOE, ANOVA, SPC, PID, scikit-learn

- Developed a software-in-the-loop deposition platform coupling a dynamic Python chamber model with compiled C++ recipe sequencing, PID control, CRC-framed communication, interlocks, and latched fault handling.
- Executed a 40-run replicated response-surface DOE and 12 independent simulated confirmation wafers, achieving 100.34 ± 0.75 nm mean ± sample SD against an illustrative 100 nm target; implemented I-MR/EWMA monitoring and process-capability analysis.
- Built trace-based virtual metrology with separate training, tuning, calibration, and test wafers; achieved 0.68 nm MAE on 40 held-out synthetic wafers and quantified degradation to 4.20 nm under unseen simulated chamber drift.

For a shorter two-bullet version, keep the first bullet and combine the DOE and VM methods without cramming every metric onto the resume. Every number above comes from `reports/reference/metrics.json` with seed 7. They describe synthetic outcomes only.

Do not claim hardware implementation, STM32 deployment, UART validation, real-time control, semiconductor tool operation, actual deposition, measured film properties, yield improvement, or production accuracy. Portable C++ source is present; a validated STM32 port is a future milestone.

## A two-minute demonstration

1. Show the cycle plot: explain how pump-down, heating, sustained stability qualification, deposition, purge and cooldown constrain actuation.
2. Open the DOE plot: explain why axial points are needed for curvature, why replicates supply pure error, and why confirmation wafers are separate from fitted observations.
3. Open the SPC chart: distinguish the illustrative 95/105 nm specifications from estimated control limits. Mention the retained Phase I signals and the one pre-drift EWMA signal.
4. Open the VM parity and residual plots: show how the held-out result compares to the training-mean baseline, then show failure under unmeasured surface drift.
5. Run `python -m fabtwin.cli faults --out runs/faults` and show why a plausible temperature-sensor bias can escape threshold interlocks.

## Questions you should be able to answer

**Why this model?** A tractable thermal/vacuum/flow surrogate lets the project focus on controller integration and manufacturing methods. Coefficients are uncalibrated. It cannot predict any real material or tool.

**Why C++?** The actual control core executes in compiled code with fixed-size state and no OS dependency. The current host bridge simulates serial bytes. Moving that core to a Nucleo requires a tested adapter, scheduling, clocks, error handling and board configuration.

**How did you prevent leakage?** Only measured deposition-trace features are inputs. Thickness and simulator-truth states are excluded. Wafers are disjoint across ordered training, tuning, interval calibration, test and drift splits.

**What does Cpk mean here?** A descriptive point estimate using an MR-based within-wafer-sequence variation estimate from the initial baseline. That baseline still has control-chart signals, so it is not accepted as a stable production process. Real capability also needs a qualified measurement system and appropriate distribution assumptions.

**What failed?** Unmeasured surface drift worsens VM error and interval coverage. Plausible sensor bias escapes simple threshold interlocks. These limitations motivate reference metrology, sensor redundancy, residual monitoring and retraining policies.

## Best next contributions

1. Add independent synthetic measurement-system variation and a Gage R&R experiment; show when metrology noise dominates capability estimates.
2. Add wafer radial temperature / thickness profiles with a clearly defined within-wafer nonuniformity metric, then optimize mean thickness and uniformity jointly.
3. Add multivariate trace monitoring or VM residual EWMA with a realistic metrology delay and sampling cadence. Keep false-alarm evaluation separate from detector tuning.
4. Implement and document the existing Nucleo port using the USB-only procedure in `STM32.md`; preserve the chamber as software.
5. Compare controller recovery after saturation, pressure disturbances and scheduling jitter across multiple independent seeds. Publish uncertainty, not a single best run.

Each extension should have a question, implementation, test, measured result and a short explanation of its limits. That makes it defendable in process and equipment interviews.
