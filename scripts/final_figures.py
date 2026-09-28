"""Figures for docs/REPORT_repair_v2.md, drawn ONLY from the FINAL report (data/repair_pilot/final_v2_report.json).

  /home/chirag/miniforge3/envs/desirna/bin/python scripts/final_figures.py
      # writes docs/figures/final_v2_umfe_time.png and final_v2_paired_effects.png

Standalone (json + matplotlib only): the ribomamba env has no matplotlib, and the pinned desirna env has
matplotlib 3.11.2 (environment.design_v2.desirna.lock.yml), so the figures are rendered there without
changing any environment.

Design: one highlight hue (blue #2a78d6, 4.3:1 on the surface) with every other method as recessive gray
context, one panel per method (identity from the panel title, never from colour alone); paired effects as a
single-hue forest plot with uMFE and NED in separate panels (no dual axis). Exact numbers are in the report's
tables, which serve as the table view.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPO_ROOT / "data" / "repair_pilot" / "final_v2_report.json"
OUT = REPO_ROOT / "docs" / "figures"
SURFACE, INK, INK2, GRID, AXIS, HIGHLIGHT, CONTEXT = ("#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7",
                                                       "#2a78d6", "#c3c2b7")
NAMES = {"rnainverse": "RNAinverse", "samfeo": "SAMFEO", "samfeo_tcdprop_efilter": "SAMFEO + TCD + screen",
         "samfeo_efilter": "SAMFEO + screen", "desirna": "DesiRNA", "tcd_sample": "TCD sampling",
         "random_pairs": "targeted random", "samplingdesign": "SamplingDesign (1 thread)"}
ORDER = list(NAMES)                    # by puzzles solved at 128 s (mean over seeds), highest first
WALLS = (1, 4, 16, 64, 128)


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=7, length=2)
    ax.grid(axis="y", color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)


def curves_figure(report: dict) -> None:
    curves = {}
    for row in report["sets"]["eterna100_v2"]["curves"]:
        curves.setdefault(row["method"], {})[row["wall_s"]] = 100 * row["success_umfe"]
    fig, axes = plt.subplots(2, 4, figsize=(10, 5.0), sharex=True, sharey=True, dpi=200, facecolor=SURFACE)
    for ax, focal in zip(axes.flat, ORDER):
        style(ax)
        for m in ORDER:
            if m != focal:
                ax.plot(WALLS, [curves[m][w] for w in WALLS], color=CONTEXT, linewidth=0.8, zorder=1)
        y = [curves[focal][w] for w in WALLS]
        ax.plot(WALLS, y, color=HIGHLIGHT, linewidth=2.0, marker="o", markersize=4,
                markeredgecolor=SURFACE, markeredgewidth=0.8, zorder=3)
        ax.annotate(f"{y[-1]:.0f} %", (WALLS[-1], y[-1]), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=7, color=INK)
        ax.annotate(f"{y[0]:.0f} %", (WALLS[0], y[0]), xytext=(4, 6 if y[0] < 60 else -11), textcoords="offset points",
                    ha="left", fontsize=7, color=INK2)
        ax.set_title(NAMES[focal], fontsize=8.5, color=INK, loc="left")
        ax.set_xscale("log", base=2)
        ax.set_xticks(WALLS, [str(w) for w in WALLS])
        ax.set_ylim(0, 85)
        ax.set_yticks([0, 20, 40, 60, 80])
        ax.set_xlim(0.8, 170)
    fig.supxlabel("method time per run (s, log scale; one core, 128 s budget)", fontsize=8, color=INK2)
    fig.supylabel("Eterna100 V2 puzzles solved, uMFE (%, mean over 3 seeds)", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0.01, 0.01, 1, 1))
    fig.savefig(OUT / "final_v2_umfe_time.png", facecolor=SURFACE)
    plt.close(fig)


ROWS = [("samfeo_efilter", "samfeo"), ("samfeo_tcdprop_efilter", "samfeo"),
        ("samfeo_tcdprop_efilter", "samfeo_efilter"), ("rnainverse", "samfeo_efilter"), ("tcd_sample", "random_pairs")]


def forest_figure(report: dict) -> None:
    paired = {(p["a"], p["b"], p["metric"], p["wall_s"]): p for p in report["sets"]["eterna100_v2"]["paired"]}
    labels = [f"{NAMES[a]}\n  minus {NAMES[b]}" for a, b in ROWS]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True, dpi=200, facecolor=SURFACE)
    panels = [("success_umfe", 100, "Success: puzzles solved (uMFE)",
               "difference at 128 s, percentage points (> 0 favours the first method)"),
              ("best_ned", 1000, "Ensemble quality: best NED",
               "difference at 128 s, ×1000 (< 0 favours the first method)")]
    for ax, (metric, scale, title, xlabel) in zip(axes, panels):
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, linewidth=0.5)
        ax.axvline(0, color=INK2, linewidth=0.8, zorder=1)
        for k, (a, b) in enumerate(ROWS):
            p = paired[(a, b, metric, 128)]
            y = len(ROWS) - 1 - k
            ax.plot([p["low"] * scale, p["high"] * scale], [y, y], color=HIGHLIGHT, linewidth=2.0,
                    solid_capstyle="round", zorder=2)
            ax.plot(p["mean_diff"] * scale, y, "o", color=HIGHLIGHT, markersize=6, markeredgecolor=SURFACE,
                    markeredgewidth=1.0, zorder=3)
            if p["n"] != 100:
                ax.annotate(f"n = {p['n']}", (p["high"] * scale, y), xytext=(5, -3), textcoords="offset points",
                            fontsize=6.5, color=INK2)
        ax.set_yticks(range(len(ROWS)), labels[::-1], fontsize=7.5, color=INK)
        ax.set_xlabel(xlabel, fontsize=8, color=INK2)
        ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "final_v2_paired_effects.png", facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    report = json.loads(REPORT.read_text())
    if report.get("status") != "FINAL":
        raise SystemExit(f"{REPORT} is not a FINAL report (status {report.get('status')!r})")
    OUT.mkdir(parents=True, exist_ok=True)
    curves_figure(report)
    forest_figure(report)
    print(f"figures from {REPORT.name} (generated {report['provenance']['generated_utc']}, "
          f"commit {report['provenance']['git_commit'][:7]}) written to {OUT}")


if __name__ == "__main__":
    main()
