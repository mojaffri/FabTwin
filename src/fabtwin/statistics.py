"""Manufacturing statistics with explicit Phase I / Phase II separation."""

import numpy as np
import pandas as pd


def _sample(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or len(x) < 3 or not np.isfinite(x).all():
        raise ValueError("Need at least three finite observations")
    return x


def capability(x, lsl=95, usl=105):
    x = _sample(x)
    if not np.isfinite([lsl, usl]).all() or lsl >= usl:
        raise ValueError("Invalid specification limits")
    mean = float(x.mean())
    within = float(np.abs(np.diff(x)).mean() / 1.128)
    overall = float(x.std(ddof=1))
    if min(within, overall) <= 0:
        raise ValueError("Capability is undefined for zero variation")
    return dict(
        n=len(x),
        mean_nm=mean,
        sigma_within_nm=within,
        sigma_overall_nm=overall,
        Cp=(usl - lsl) / (6 * within),
        Cpk=min(usl - mean, mean - lsl) / (3 * within),
        Pp=(usl - lsl) / (6 * overall),
        Ppk=min(usl - mean, mean - lsl) / (3 * overall),
        observed_in_spec_fraction=float(((x >= lsl) & (x <= usl)).mean()),
    )


def monitor(reference, future, lam=0.2, width=3.0):
    reference, future = _sample(reference), _sample(future)
    if not 0 < lam <= 1 or not np.isfinite(width) or width <= 0:
        raise ValueError("Invalid EWMA parameters")
    center = float(reference.mean())
    mr_bar = float(np.abs(np.diff(reference)).mean())
    sigma = mr_bar / 1.128
    if sigma <= 0:
        raise ValueError("Zero reference variation")
    z, rows = center, []
    previous = reference[-1]
    for i, x in enumerate(future, 1):
        z = lam * x + (1 - lam) * z
        bound = width * sigma * np.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * i)))
        mr = abs(x - previous)
        rows.append(
            dict(
                value=x,
                ewma=z,
                ewma_lcl=center - bound,
                ewma_ucl=center + bound,
                individual_lcl=center - 3 * sigma,
                individual_ucl=center + 3 * sigma,
                moving_range=mr,
                mr_ucl=3.267 * mr_bar,
                individual_alarm=bool(abs(x - center) > 3 * sigma),
                ewma_alarm=bool(abs(z - center) > bound),
                mr_alarm=bool(mr > 3.267 * mr_bar),
            )
        )
        previous = x
    phase1_signals = int((abs(reference - center) > 3 * sigma).sum())
    phase1_mr_signals = int((np.abs(np.diff(reference)) > 3.267 * mr_bar).sum())
    return pd.DataFrame(rows), dict(
        center=center,
        sigma=sigma,
        phase1_individual_signals=phase1_signals,
        phase1_mr_signals=phase1_mr_signals,
        lag1_correlation=float(np.corrcoef(reference[:-1], reference[1:])[0, 1]),
        note="Capability is descriptive/provisional. Phase I I-MR screening alone does not establish normality or stability.",
    )
