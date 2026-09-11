# Chamber model and assumptions

This is a single-wafer, lumped CVD-like model with generic reactant availability. No actual precursor, chemical handling instructions, or production recipe is specified. All coefficients below are chosen for an educational simulation and are uncalibrated.

## States and units

| Symbol | Meaning | Unit / range |
|---|---|---|
| T | Lumped chamber / wafer temperature | °C |
| P | Chamber pressure | Torr |
| F | Actual mass-flow-controller flow | sccm |
| c | Normalized reactive-gas availability | 0–1 |
| h | Film thickness | nm |
| u | Heater command | 0–1 |
| v | Exhaust throttle opening | 0–1 |
| g | Wafer / chamber growth multiplier | dimensionless |

## Dynamics

Thermal energy balance surrogate:

`dT/dt = [950 η u − (T − 25)] / 80`

The 80 s thermal time constant represents lumped heat capacity divided by heat loss. Heater efficiency η defaults to 1. The 950 °C gain represents heater power divided by heat loss, not a material property.

MFC dynamics: `dF/dt = (F_command − F) / 0.8`.

Vacuum balance: `dP/dt = [0.02 + 0.01267 F + leak − (0.08 + 0.92 v) P] / 2`.

This corresponds to an effective volume of 2 L, pump speed of 0.08–1 L/s, and gas throughput in Torr·L/s. The 0.01267 coefficient approximately converts sccm to Torr·L/s at standard conditions; gas-temperature corrections and real pump curves are deliberately omitted. The baseline throughput is 0.02 Torr·L/s. Pump-down begins at 5 Torr, representing an already evacuated chamber. There is no atmospheric loading model.

Reactive gas availability: `dc/dt = (precursor_gate − c) / 2`. A two-second wash-in/wash-out lag represents chamber residence and residual precursor. This is not a full species balance. Purge can continue depositing a small residual film while c decays. Availability is independent of detailed surface consumption.

Growth:

`dh/dt = 0.83 × exp[2200 (1/723.15 − 1/(T+273.15))] × [P/(P+1)]/0.75 × [F/(F+50)]/(2/3) × c × g`

At the nominal steady state, the base growth rate is 0.83 nm/s. The Arrhenius-like coefficient has units K, corresponding to an illustrative effective activation energy `2200 R ≈ 18.3 kJ/mol`. Saturation terms mimic limited transport/reactant response. Pressure and flow sensitivities are phenomenological and are not independently derived chemistry.

Each wafer has a lognormal growth multiplier with mean 1 and approximately 0.8% standard deviation. Temperature, pressure, and flow sensors have independent Gaussian noise with SD 0.15 °C, 0.003 Torr, and 0.15 sccm. Simulated thickness metrology adds independent 0.25 nm SD noise. Random streams are seeded. No real metrology calibration has been performed.

## Integration and controls

The default step is 0.25 s. Temperature and pressure use exact first-order updates with held inputs; MFC and reactive availability also use exact first-order updates. The coupled updates are sequential and thickness uses an endpoint rate. This is first-order operator splitting, not an exact solution of the full coupled system. A 0.125 s convergence regression checks nominal thickness agreement within 1 nm.

The temperature PID uses heater feedforward `(T_set−25)/950`, bounded output, filtered derivative on measurement, and conditional integration. Pressure PID reverses the error sign because opening the exhaust reduces pressure. Ten consecutive seconds inside temperature, pressure, and flow windows are required before deposition. A temporary in-window crossing is insufficient.

## Unmodeled effects

There is no radial wafer grid, film composition, plasma physics, nucleation/incubation, surface stress, defect density, feature-scale transport, or chamber maintenance model. Temperature stands in for both wafer and chamber temperature. Conditions are not suitable for real chemical-process operation. The correct claim is a **physics-inspired process-control simulator**, not a validated physical twin.
