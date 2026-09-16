import numpy as np
import pandas as pd
import pytest

from fabtwin.measurement import analyze, study


def test_crossed_anova_known_components():
    data = pd.DataFrame(
        [
            dict(part=p, operator=o, repeat=r, thickness_nm=100 + p * 2 + o * 0.4 + e)
            for p in range(4)
            for o in range(3)
            for r, e in enumerate([-0.1, 0.1])
        ]
    )
    m = analyze(data)
    assert m["variance_components_nm2"]["repeatability"] == pytest.approx(0.02)
    assert m["variance_components_nm2"]["operator"] == pytest.approx(0.16)
    assert m["variance_components_nm2"]["interaction"] == 0
    assert m["grr_sigma_nm"] == pytest.approx(np.sqrt(0.18))


def test_missing_and_duplicate_measurements_rejected():
    data = study()
    for bad in [data.iloc[:-1], pd.concat([data, data.iloc[:1]])]:
        with pytest.raises(ValueError):
            analyze(bad)
    data["thickness_nm"] = 100.0
    with pytest.raises(ValueError):
        analyze(data)


def test_noise_study_is_reproducible_and_degrades_gage():
    pd.testing.assert_frame_equal(study(), study())
    assert (
        analyze(study(repeat_sigma=1))["percent_tolerance"] > analyze(study())["percent_tolerance"]
    )
