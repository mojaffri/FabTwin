import numpy as np
import pytest

from fabtwin.model import Recipe
from fabtwin.simulation import FEATURES
from fabtwin.statistics import capability, monitor


def test_capability_uses_moving_range_and_distinguishes_overall():
    x = np.array([98, 100, 102, 100, 98, 100, 102, 100], dtype=float)
    result = capability(x)
    assert result["sigma_within_nm"] == pytest.approx(2 / 1.128)
    assert result["Cp"] == pytest.approx(10 / (6 * (2 / 1.128)))
    assert result["Cpk"] == pytest.approx(result["Cp"])
    assert result["Pp"] == pytest.approx(10 / (6 * x.std(ddof=1)))


def test_ewma_recurrence_limits_and_freezing():
    baseline = [99, 100, 101, 100] * 10
    chart, _ = monitor(baseline, [102, 104, 106], lam=0.2)
    assert chart.ewma.tolist() == pytest.approx([100.4, 101.12, 102.096])
    changed, _ = monitor(baseline, [102, 104, 900], lam=0.2)
    assert changed.individual_ucl.tolist() == chart.individual_ucl.tolist()
    assert changed.ewma_ucl.tolist() == chart.ewma_ucl.tolist()


@pytest.mark.parametrize("bad", [[1, 1, 1], [1, 2, float("nan")], []])
def test_invalid_capability_rejected(bad):
    with pytest.raises(ValueError):
        capability(bad)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(temperature_c=999),
        dict(pressure_torr=float("nan")),
        dict(flow_sccm=-1),
        dict(deposition_s=0),
    ],
)
def test_invalid_recipe(kwargs):
    with pytest.raises(ValueError):
        Recipe(**kwargs)


def test_vm_truth_is_not_a_feature():
    forbidden = {
        "truth_thickness_nm",
        "measured_thickness_nm",
        "truth_temperature_c",
        "surface_gain",
        "seed",
        "split",
        "wafer",
        "fault",
    }
    assert forbidden.isdisjoint(FEATURES)
