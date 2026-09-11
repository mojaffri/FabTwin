import numpy as np
import pandas as pd
import pytest

from fabtwin.experiments import bootstrap_mae_interval, nominal_kinetics_prediction


def test_nominal_kinetics_baseline_has_known_units_and_rate():
    data = pd.DataFrame(
        {"thermal_dose": [120.0, 60.0], "pressure_mean": [3.0, 3.0], "flow_mean": [100.0, 100.0]}
    )
    assert nominal_kinetics_prediction(data).tolist() == pytest.approx([99.6, 49.8])


def test_bootstrap_interval_is_reproducible_and_contains_constant_error():
    y = np.arange(40.0)
    assert bootstrap_mae_interval(y, y + 2) == pytest.approx([2.0, 2.0])
    a = bootstrap_mae_interval(y, y + np.linspace(0, 2, 40))
    assert a == bootstrap_mae_interval(y, y + np.linspace(0, 2, 40))
    assert a[0] < 1 < a[1]


def test_bootstrap_rejects_nonfinite_results():
    with pytest.raises(ValueError):
        bootstrap_mae_interval([1, 2], [1, np.nan])
