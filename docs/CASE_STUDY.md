# Engineering case study: controlling a virtual deposition tool

## Question

Can one inspectable workflow connect equipment control, process characterization, manufacturing monitoring and virtual metrology without physical process hardware?

FabTwin answers this with a software chamber and an actual compiled C++ controller. The results establish a working software integration and illustrate engineering methods. They do not validate a real deposition process.

## What the experiment established

| Decision | Evidence from the reference run | Interpretation |
|---|---|---|
| Qualify recipe conditions before deposition | Nominal cycle completed with sustained temperature, pressure and flow qualification | State transitions depend on measured conditions, not only timers |
| Use a quadratic DOE | Full-rank 40-run replicated design; lack-of-fit p ≈ 0.44 | No detected lack of fit at this design's precision; this is not proof of physical correctness |
| Confirm the selected settings independently | 12 fresh wafers: 100.34 ± 0.75 nm, mean ± sample SD | A local target-matching recipe worked in the synthetic model |
| Freeze monitoring limits before introducing drift | Thickness EWMA signals 9 wafers after drift onset, with 1 pre-drift flagged wafer out of 80 | Detection delay must be reported alongside false flags and baseline diagnostics |
| Challenge ML with a strong simple benchmark | Held-out MAE: mean predictor 4.67 nm; nominal kinetics 0.63 nm; selected ML 0.68 nm | ML improves over the mean but does not beat the matched kinetics baseline in this run |
| Evaluate an unseen chamber change | ML MAE rises to 4.20 nm; interval coverage falls to 22.5% | The learned model is vulnerable to a hidden change that trace inputs cannot fully identify |
| Use measured residuals as an additional monitor | Residual EWMA signals after 11 affected wafers; 0 pre-drift flags among 40 | Reference metrology can reveal drift, but detection waits for that metrology |

## What changed during hardening

The original controller checked hard equipment limits and qualified conditions before deposition. It could still continue a deposition cycle when temperature or flow moved substantially away from the recipe without crossing a hard limit. The release adds a separate, debounced process-window fault. Tests cover short excursions, recovery, and sustained deviations.

A reset command during an active recipe could also momentarily suppress the actuator command. It now produces an explicit recipe fault, avoiding ambiguous partial-cycle behavior. A communication-silence watchdog, CRC checks, sequence checks and safe reset resynchronization have their own tests.

## The strongest interview lesson

Known process structure can be more valuable than extra model complexity. The nominal-kinetics benchmark shares the simulator's equations and nominal coefficients, so its advantage is expected and transparent. On a real process, that structure would need calibration and validation. The useful comparison is whether data-driven corrections add value beyond a credible baseline—not whether an ML model fits synthetic data well.

The reported Cp/Cpk values remain descriptive because the baseline includes retained I-MR signals. No points were deleted to manufacture a clean chart. A next iteration should investigate measurement-system variation, baseline stability, and detection performance across independent campaigns before making stronger process-capability or fault-detection claims.

See the [generated report](../reports/reference/REPORT.md), [raw metrics](../reports/reference/metrics.json), and [validation record](VALIDATION.md). Every measurement in this case study is simulated.
