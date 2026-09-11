"""Run from repository root after installing and building the controller."""

from fabtwin.model import Disturbance, Recipe
from fabtwin.simulation import simulate

nominal = simulate(Recipe(), seed=7)
print(nominal.summary)
fault = simulate(disturbance=Disturbance("door_open", 150))
print({key: fault.summary[key] for key in ["state", "fault", "cycle_s"]})
