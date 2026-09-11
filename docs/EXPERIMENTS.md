# Experiment design and interpretation

## DOE / response surface

Factors are coded as `T=(temperature−450)/15`, `P=(pressure−3)/0.4`, and `F=(flow−100)/15`. Deposition lasts 120 s. Two replicates each of eight cube corners and six face centers plus twelve center runs yield 40 wafers. Randomized order reduces confounding with run order. Independent wafer draws are physical-process analogs; sensor samples within a wafer are not counted as experimental replicates.

The full quadratic has ten coefficients: intercept, three main effects, three pair interactions, and three squares. The face-centered design has three factor levels and is not rotatable. Unlike a two-level factorial alone, it can identify the separate quadratic terms. Replicates provide pure error and allow a lack-of-fit F test: `(SS_LOF / df_LOF) / (SS_pure / df_pure)`. ANOVA is Type II; inspect residual plots, not p-values alone.

A 21³ bounded candidate grid finds the prediction closest to 100 nm. This target-matching objective does not optimize film quality, uniformity, throughput, or cost. Twelve independently seeded confirmation wafers check the selected setting. A model with significant lack of fit remains an approximation even if the confirmation mean is close to target. `process_window.csv` exposes all candidates so the objective can be changed.

## SPC and capability

The first 80 of 260 wafers form Phase I. After wafer 160, an unmeasured chamber-surface multiplier increases by 0.15% of nominal per wafer. The recipe is fixed; limits never refit to later data. Monitoring starts at wafer 81 and includes 80 stable future wafers before drift.

Individual limits use `mean ± 3 × MRbar/1.128`, where moving ranges use consecutive pairs. MR UCL is `3.267 MRbar` and LCL is zero. EWMA uses λ=0.2 and finite-startup limits with variance factor `λ/(2−λ) × [1−(1−λ)^(2t)]`.

Cp/Cpk use MR-based within variation; Pp/Ppk use the overall sample SD. Both are calculated only on the Phase I baseline and clearly labeled descriptive/provisional. The report retains any baseline signals instead of silently deleting inconvenient points. Lag-one correlation is reported. Normality, independence, stability, rational sampling, measurement-system adequacy, and uncertainty of capability estimates require further assessment; no production acceptance claim follows from these point estimates.

An EWMA alarm count is a count of flagged wafers, not independent alarm events or a validated long-run false-alarm probability. Detection delay is the first post-onset signal wafer minus the first affected wafer; same-wafer detection has delay zero. These charts assume one delayed thickness measurement becomes available before the next wafer is evaluated. They do not represent real-time endpoint metrology.

## Virtual metrology

The 300 wafers have randomized recipes and ordered, disjoint splits: 140 train / 40 tune / 40 interval calibration / 40 in-distribution test / 40 drift challenge. Each row summarizes a complete deposition trace. None of the splits share wafers or seeds. The synthetic chamber gain drifts only in the last 40 wafers; ordinary wafer variation is independent throughout.

An explicit feature allowlist includes sensor means and SDs, heater effort, deposition time, measured thermal dose, and measured flow dose. Truth thickness, true temperature, true growth rate, chamber gain, fault label, seed, wafer index, and split label are excluded. Thickness from simulated metrology is the training target, never an input.

Two baselines accompany the ML score: a training-mean predictor and a fixed nominal-kinetics calculation from measured thermal dose, pressure and flow. The latter deliberately shares the simulator's nominal functional form and coefficients, giving it a structural advantage. It has no hidden wafer gain or true temperature inputs. A strong result from this simple baseline is evidence that extra ML complexity is not automatically useful in a known-model simulation.

The held-out test MAE includes an independent-wafer bootstrap percentile interval (2,000 resamples, 95%). The drift block does not receive an IID bootstrap interpretation. A separate EWMA monitors measured-minus-predicted residuals using frozen calibration residual limits; the saved report includes pre-drift flags and detection delay. This requires delayed reference metrology and is not a sensor-only early-warning system. Calibration diagnostics are retained if the residual baseline has signals.

Three quadratic Ridge regularizations and one random forest are fit on training data and selected by tuning MAE. The selected estimator is not refit afterward. Absolute residuals on the separate calibration set establish a 90% split-conformal interval using a finite-sample order statistic. Test and drift outcomes do not influence selection or calibration. Report MAE/RMSE/R², training-mean baseline MAE, and empirical interval coverage separately for test and drift.

The calibration interpretation requires exchangeability. The drift challenge deliberately violates it. It shows how a model trained only on available traces can miss an unmeasured chamber change. Poor drift coverage is a useful finding, not something to tune away using the test set.

`vm/model.joblib` contains the fitted estimator, feature list and interval radius. Load only model files you trust; Python serialization is executable. Rerunning `vm` reproduces the artifact. A deployment example is in `examples/predict_thickness.py`.

## Fault experiments

Door open, emergency stop, stale telemetry and overpressure cause immediate or next-sample faults. Heater degradation causes a state timeout when target conditions cannot be reached. A plausible +8 °C sensor bias can pass the interlocks and change actual film thickness. Distinguish equipment protection from process fault detection: thresholds alone cannot identify all bad wafers.

A seventh case degrades the heater after deposition begins. A sustained process-temperature excursion trips the separate `PROCESS_WINDOW` interlock. Native C++ tests verify that a brief excursion does not trip and that continuous deviation does.
