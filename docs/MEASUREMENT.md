# Measurement-system sensitivity study

Before interpreting a thickness capability index, ask how much of the observed variation comes from the measurement system. This extension keeps FabTwin centered on deposition process characterization and metrology.

Run `python -m fabtwin.measurement --seed 7 --out runs/measurement`. The included evidence lives in `reports/measurement/`. It is an independent synthetic measurement experiment, not repeated measurements from actual deposition wafers and not a change to the original deposition simulator's measurement noise.

The balanced crossed design has 10 synthetic parts, 3 operators and 3 repeats per part/operator, for 90 readings in randomized row order. Part variation, operator offsets, part/operator interaction and repeat noise are drawn separately. The nominal gage uses 0.20 nm repeat-noise SD; the noisy comparison uses 1.00 nm. Both use the same seed and part/operator effects to isolate measurement-noise sensitivity.

The model is `reading = grand mean + part effect + operator effect + interaction + repeat error`. Unpooled crossed random-effects ANOVA estimates repeatability, operator, interaction and part variance. Negative variance component estimates are truncated at zero and retained in the description; no statistical significance pooling is applied. Three operators give an imprecise operator-variance estimate, so the study should not be presented as certification of a measurement system.

Gage R&R SD combines repeatability, operator and interaction variances. Percent tolerance is `100 × 6 × sigma_GRR / (USL−LSL)` for the illustrative 10 nm tolerance width. Percent study variation uses GRR SD divided by total SD, so it is different from percent variance contribution.

Seed 7 results:

| Measurement scenario | Gage R&R SD / nm | Percent tolerance | Percent study variation |
|---|---:|---:|---:|
| Nominal | 0.193 | 11.58% | 18.37% |
| Noisy gage | 0.963 | 57.77% | 66.83% |

The result is sensitivity evidence: a measurement system can consume much of a narrow film-thickness tolerance even when the underlying process is unchanged. The script does not assign an industrial acceptance category or claim a universal acceptance threshold. Real use requires representative parts, operators, traceability, bias/linearity studies and an appropriate sampling design.

Automated checks cover known ANOVA variance components, missing/duplicate observations and reproducible noise sensitivity. This extension leaves the original reference experiment and its source hashes intact.
