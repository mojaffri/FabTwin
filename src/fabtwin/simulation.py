from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .model import Chamber, Disturbance, Recipe
from .protocol import Controller

# Explicit allowlist: no truth temperature, thickness, rate, seed, gain, or fault labels.
FEATURES = [
    "temperature_mean",
    "temperature_std",
    "pressure_mean",
    "pressure_std",
    "flow_mean",
    "flow_std",
    "heater_mean",
    "deposition_time",
    "thermal_dose",
    "flow_dose",
]


@dataclass
class Run:
    trace: pd.DataFrame
    summary: dict


def simulate(recipe=None, seed=7, disturbance=None, surface_gain=1.0, dt=0.25):
    recipe, disturbance = recipe or Recipe(), disturbance or Disturbance()
    if not np.isfinite(dt) or not 0 < dt <= 0.5:
        raise ValueError("dt must be in (0, 0.5]")
    chamber = Chamber(seed, surface_gain)
    rows = []
    with Controller() as controller:
        for step in range(int(1800 / dt)):
            now = step * dt
            sensor = chamber.measure(now, disturbance)
            stamp = now - 2 if disturbance.kind == "stale" and now >= disturbance.onset_s else now
            output = controller.step(
                now, sensor, recipe, command=1 if step == 0 else 0, stamp=stamp
            )
            rows.append(
                dict(
                    time_s=now,
                    temperature_c=sensor[0],
                    pressure_torr=sensor[1],
                    flow_sccm=sensor[2],
                    truth_temperature_c=chamber.t,
                    truth_thickness_nm=chamber.h,
                    **output,
                )
            )
            if output["state"] in {"FAULT", "COMPLETE"}:
                break
            chamber.advance(output, dt, now, disturbance)
        else:
            raise RuntimeError("Simulation exceeded wall-clock recipe limit")
    trace = pd.DataFrame(rows)
    process = trace.loc[trace.state == "DEPOSITION"]
    summary = dict(
        seed=seed,
        **asdict(recipe),
        state=output["state"],
        fault=output["fault"],
        cycle_s=now,
        truth_thickness_nm=chamber.h,
        measured_thickness_nm=chamber.h + np.random.default_rng(seed + 1000000).normal(0, 0.25),
    )
    if len(process):
        for field, column in [
            ("temperature", "temperature_c"),
            ("pressure", "pressure_torr"),
            ("flow", "flow_sccm"),
        ]:
            summary[field + "_mean"] = float(process[column].mean())
            summary[field + "_std"] = float(process[column].std(ddof=0))
        summary.update(
            heater_mean=float(process.heater.mean()),
            deposition_time=len(process) * dt,
            thermal_dose=float(
                np.exp(2200 * (1 / 723.15 - 1 / (process.temperature_c + 273.15))).sum() * dt
            ),
            flow_dose=float(process.flow_sccm.sum() * dt),
        )
    return Run(trace, summary)
