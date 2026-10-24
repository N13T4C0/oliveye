"""Static figures of the model results (notebook 04 and docs/results).

Colour roles (validated with the dataviz palette checker, all pairs, light surface):
the aforo, the main model and the naive baseline are categorical slots 1-3; the real
production is drawn in text ink because it is the reference, not a competing series.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

SURFACE = "#fcfcfb"
INK = "#163300"  # DESIGN.md --ink: the real production
MUTED = "#6a6c6a"  # DESIGN.md --muted: axes, grid labels
GRID = "#e8ebe6"  # DESIGN.md --fog
SERIES = {
    "aforo": ("#2a78d6", "Aforo (Junta)"),
    "ridge": ("#eb6834", "OlivEye (Ridge)"),
    "last_campaign": ("#1baf7a", "Repeat last campaign"),
}


def _style(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def production_vs_aforo(
    predictions: pd.DataFrame, baselines: pd.DataFrame, *, interval_factor: float
) -> Figure:
    """One panel per province: real production, aforo, model (with its interval) and last year.

    `interval_factor` is the conformal multiplicative half-width (forecast / f .. forecast · f).
    Each panel has its own y-axis in thousand tonnes (the provinces differ ~4x in size).
    """
    merged = baselines.merge(
        predictions[["campaign", "province", "pred_t"]], on=["campaign", "province"], how="inner"
    ).sort_values("campaign")
    provinces = sorted(merged["province"].unique(), key=lambda p: p != "Jaén")
    fig, axes = plt.subplots(1, len(provinces), figsize=(5.2 * len(provinces), 3.6))
    fig.patch.set_facecolor(SURFACE)
    for ax, province in zip(np.atleast_1d(axes), provinces, strict=True):
        rows = merged[merged["province"] == province]
        x = np.arange(len(rows))
        kt = 1e-3
        ax.fill_between(
            x,
            rows["pred_t"] / interval_factor * kt,
            rows["pred_t"] * interval_factor * kt,
            color=SERIES["ridge"][0],
            alpha=0.12,
            linewidth=0,
            label="80 % interval",
        )
        for key, column in (
            ("last_campaign", "pred_last_t"),
            ("aforo", "pred_aforo_t"),
            ("ridge", "pred_t"),
        ):
            color, label = SERIES[key]
            ax.plot(
                x,
                rows[column] * kt,
                color=color,
                linewidth=2,
                marker="o",
                markersize=4,
                label=label,
            )
        ax.plot(
            x,
            rows["oil_final_t"] * kt,
            color=INK,
            linewidth=2.4,
            marker="s",
            markersize=5,
            label="Real production",
        )
        ax.set_xticks(x, rows["campaign"], rotation=45, ha="right")
        ax.set_title(province, loc="left", color=INK, fontsize=11, fontweight="bold")
        ax.set_ylabel("Olive oil (thousand t)", color=MUTED, fontsize=9)
        ax.set_ylim(bottom=0)
        _style(ax)
    handles, labels = np.atleast_1d(axes)[0].get_legend_handles_labels()
    order = [labels.index("Real production"), *range(len(labels) - 1)]  # reference first
    fig.legend(
        [handles[k] for k in order],
        [labels[k] for k in order],
        loc="upper center",
        ncol=5,
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.5, 1.04),
    )
    fig.tight_layout()
    return fig


def error_by_campaign(per_campaign: pd.DataFrame) -> Figure:
    """Dot plot of the mean |log error| per campaign (0.1 ≈ 10 % off), one row per campaign."""
    table = per_campaign.sort_index(ascending=False)
    y = np.arange(len(table))
    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(table) + 1.2))
    fig.patch.set_facecolor(SURFACE)
    for offset, key in zip((-0.18, 0.0, 0.18), ("last_campaign", "aforo", "ridge"), strict=True):
        if key not in table:
            continue
        color, label = SERIES[key]
        ax.scatter(
            table[key],
            y + offset,
            s=36,
            color=color,
            edgecolors=SURFACE,
            linewidths=1.5,
            label=label,
            zorder=3,
        )
    ax.set_yticks(y, table.index)
    ax.set_xlabel("Mean |log error| per campaign (0.1 ≈ 10 % off)", color=MUTED, fontsize=9)
    ax.set_xlim(left=0)
    _style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.1), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout()
    return fig
