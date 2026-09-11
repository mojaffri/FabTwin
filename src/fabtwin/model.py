"""Lumped, uncalibrated CVD-like surrogate. No chemistry or hardware is operated."""

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Recipe:
    temperature_c: float = 450.0
    pressure_torr: float = 3.0
    flow_sccm: float = 100.0
    deposition_s: float = 120.0

    def __post_init__(self):
        for name, lo, hi in [
            ("temperature_c", 400, 500),
            ("pressure_torr", 1, 5),
            ("flow_sccm", 50, 150),
            ("deposition_s", 30, 240),
        ]:
            value = getattr(self, name)
            if not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f"{name} must be finite and between {lo} and {hi}")


@dataclass(frozen=True)
class Disturbance:
    kind: str = "none"
    onset_s: float = 120.0
    magnitude: float = 0.0

    def __post_init__(self):
        if self.kind not in {
            "none",
            "sensor_bias",
            "heater_loss",
            "vacuum_leak",
            "door_open",
            "estop",
            "stale",
        }:
            raise ValueError("Unknown disturbance")
        if (
            not math.isfinite(self.onset_s)
            or self.onset_s < 0
            or not math.isfinite(self.magnitude)
            or self.magnitude < 0
        ):
            raise ValueError("Disturbance onset and magnitude must be nonnegative and finite")
        if self.kind == "heater_loss" and self.magnitude > 1:
            raise ValueError("Heater loss must be in [0, 1]")


class Chamber:
    def __init__(self, seed=7, surface_gain=1.0):
        if not math.isfinite(surface_gain) or surface_gain <= 0:
            raise ValueError("surface_gain must be positive")
        self.rng = np.random.default_rng(seed)
        self.t, self.p, self.flow, self.c, self.h = 25.0, 5.0, 0.0, 0.0, 0.0
        self.gain = surface_gain * self.rng.lognormal(-0.5 * 0.008**2, 0.008)

    def measure(self, now, disturbance):
        active = now >= disturbance.onset_s
        bias = disturbance.magnitude if active and disturbance.kind == "sensor_bias" else 0
        return (
            self.t + bias + self.rng.normal(0, 0.15),
            max(0, self.p + self.rng.normal(0, 0.003)),
            max(0, self.flow + self.rng.normal(0, 0.15)),
            not (active and disturbance.kind == "door_open"),
            active and disturbance.kind == "estop",
        )

    def advance(self, output, dt, now, disturbance):
        if not 0 < dt <= 0.5:
            raise ValueError("Use a timestep in (0, 0.5] seconds")
        active = now >= disturbance.onset_s
        efficiency = (
            1 - disturbance.magnitude if active and disturbance.kind == "heater_loss" else 1
        )
        leak = disturbance.magnitude if active and disturbance.kind == "vacuum_leak" else 0
        self.t = (
            25
            + 950 * output["heater"] * efficiency
            + (self.t - 25 - 950 * output["heater"] * efficiency) * math.exp(-dt / 80)
        )
        self.flow += (output["flow_command"] - self.flow) * (1 - math.exp(-dt / 0.8))
        pumping = 0.08 + 0.92 * output["throttle"]
        equilibrium = (0.02 + 0.01267 * self.flow + leak) / pumping
        self.p = equilibrium + (self.p - equilibrium) * math.exp(-pumping * dt / 2)
        self.c += (float(output["precursor"]) - self.c) * (1 - math.exp(-dt / 2))
        rate = 0.83 * math.exp(2200 * (1 / 723.15 - 1 / (self.t + 273.15)))
        rate *= (
            (self.p / (self.p + 1) / 0.75)
            * (self.flow / (self.flow + 50) / (2 / 3))
            * self.c
            * self.gain
        )
        self.h += rate * dt
