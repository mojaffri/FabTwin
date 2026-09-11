"""Static, exportable engineering figures; no server or web stack required."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BLUE, TEAL, RED = "#2456A6", "#00877A", "#C44D45"


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#344256",
            "text.color": "#182C46",
            "axes.edgecolor": "#C8D2DC",
            "grid.color": "#E6EBF0",
            "figure.facecolor": "#FAFCFE",
            "axes.facecolor": "white",
            "savefig.dpi": 160,
        }
    )


def finish(fig, path):
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def cycle(trace, path):
    style()
    fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True, layout="constrained")
    for ax, column, label in zip(
        axes,
        ["temperature_c", "pressure_torr", "truth_thickness_nm", "heater"],
        [
            "Sensor temperature / °C",
            "Sensor pressure / Torr",
            "Simulated thickness / nm",
            "Heater command / fraction",
        ],
    ):
        ax.plot(trace.time_s, trace[column], color=BLUE, lw=1.5)
        ax.set_ylabel(label)
        ax.grid(alpha=0.7)
    changes = trace.loc[trace.state.ne(trace.state.shift())]
    for _, row in changes.iterrows():
        for ax in axes:
            ax.axvline(row.time_s, color=TEAL, alpha=0.25, lw=1)
        axes[0].text(
            row.time_s,
            1.02,
            row.state,
            rotation=45,
            ha="left",
            fontsize=7,
            transform=axes[0].get_xaxis_transform(),
        )
    axes[-1].set_xlabel("Simulated time / s")
    fig.suptitle(
        "FabTwin | C++ controlled deposition cycle\nSynthetic chamber · host software-in-the-loop",
        fontsize=17,
        y=1.06,
    )
    finish(fig, path)


def doe_fig(data, grid, residual, path):
    style()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), layout="constrained")
    section = grid.loc[np.isclose(grid.F, 0)]
    pivot = section.pivot(index="T", columns="P", values="predicted_nm")
    contour = axes[0].contourf(
        3 + 0.4 * pivot.columns.to_numpy(),
        450 + 15 * pivot.index.to_numpy(),
        pivot.to_numpy(),
        levels=16,
        cmap="viridis",
    )
    fig.colorbar(contour, ax=axes[0], label="Predicted thickness / nm")
    axes[0].set(
        xlabel="Pressure / Torr",
        ylabel="Temperature / °C",
        title="Local response surface · flow 100 sccm",
    )
    axes[1].scatter(residual.fitted, residual.residual, c=BLUE, s=24)
    axes[1].axhline(0, color=TEAL)
    axes[1].set(
        xlabel="Fitted thickness / nm", ylabel="Residual / nm", title="Residuals versus fitted"
    )
    from scipy.stats import probplot

    (theoretical, ordered), (slope, intercept, _) = probplot(residual.residual)
    axes[2].scatter(theoretical, ordered, c=BLUE, s=24)
    axes[2].plot(theoretical, slope * theoretical + intercept, color=TEAL)
    axes[2].set(
        xlabel="Normal theoretical quantile",
        ylabel="Residual / nm",
        title="Normal probability diagnostic",
    )
    fig.suptitle("FabTwin | 40-run replicated DOE · synthetic outcomes", fontsize=17)
    finish(fig, path)


def spc_fig(data, chart, metrics, path):
    style()
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, layout="constrained")
    axes[0].plot(data.wafer, data.measured_thickness_nm, color=BLUE, lw=1)
    for level in [95, 105]:
        axes[0].axhline(level, color=RED, ls=":", label="Specification" if level == 95 else None)
    for column in ["individual_lcl", "individual_ucl"]:
        axes[0].plot(chart.wafer, chart[column], color=TEAL, ls="--")
    axes[0].set(
        ylabel="Thickness / nm",
        title="Individuals chart · specifications and control limits are separate",
    )
    axes[1].plot(chart.wafer, chart.ewma, color=BLUE)
    axes[1].fill_between(chart.wafer, chart.ewma_lcl, chart.ewma_ucl, color=TEAL, alpha=0.12)
    alarm = chart.loc[chart.ewma_alarm]
    axes[1].scatter(alarm.wafer, alarm.ewma, color=RED, s=12)
    axes[1].set(ylabel="EWMA / nm", title="EWMA · λ = 0.2 · limits frozen from Phase I")
    axes[2].plot(chart.wafer, chart.moving_range, color=BLUE, lw=1)
    axes[2].plot(chart.wafer, chart.mr_ucl, color=TEAL, ls="--")
    axes[2].set(ylabel="Moving range / nm", xlabel="Wafer number", title="Moving range chart")
    for ax in axes:
        ax.axvspan(1, metrics["baseline_wafers"], color="#C8D2DC", alpha=0.25)
        ax.axvline(metrics["drift_first_wafer"], color=RED, ls="--")
        ax.grid(alpha=0.5)
    fig.suptitle("FabTwin | Chamber surface drift · synthetic wafer campaign", fontsize=17)
    finish(fig, path)


def vm_fig(data, metrics, path):
    style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained")
    for split, color in [("test", BLUE), ("drift", RED)]:
        block = data.loc[data.split == split]
        axes[0].scatter(
            block.measured_thickness_nm,
            block.predicted_nm,
            color=color,
            label=split,
            alpha=0.7,
            s=24,
        )
        axes[1].scatter(
            block.wafer, block.measured_thickness_nm - block.predicted_nm, color=color, s=20
        )
    lo, hi = data.measured_thickness_nm.min(), data.measured_thickness_nm.max()
    axes[0].plot([lo, hi], [lo, hi], color=TEAL, ls="--")
    axes[0].legend()
    axes[0].set(
        xlabel="Simulated metrology / nm",
        ylabel="Virtual metrology / nm",
        title="Held-out prediction parity",
    )
    q = metrics["interval_half_width_nm"]
    axes[1].axhspan(-q, q, color=TEAL, alpha=0.12)
    axes[1].axhline(0, color=TEAL)
    axes[1].set(
        xlabel="Wafer number",
        ylabel="Measured − predicted / nm",
        title="Unmeasured drift exposes model limits",
    )
    fig.suptitle("FabTwin | Virtual metrology · chronological evaluation", fontsize=17)
    finish(fig, path)
