"""Build Figure 2 (detection scores) and Figure 3 (write-back scope)."""
from __future__ import annotations

import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

WS = r"F:\周四焜哥论文"
FIG = os.path.join(WS, "paper", "figures")
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 300, "savefig.bbox": "tight"})


def read(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fig2():
    rows = read(os.path.join(WS, "results", "runs", "rq3_detection_v2", "per_frame.csv"))
    seq, inj, L = "knight", "A", 12
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 3.6), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})
    for col, (det, title, color) in enumerate([
            ("hist_kl", "BlazeBVD Eq. (5): smoothed-histogram KL", "#8c510a"),
            ("hist_kl_cusum", "Rolling-median JS + CUSUM", "#01665e")]):
        rs = [r for r in rows if r["sequence"] == seq and r["injection"] == inj
              and int(r["length"]) == L and r["detector"] == det]
        t = [int(r["t"]) for r in rs]
        sc = [float(r["score"]) for r in rs]
        mk = [int(r["mask"]) for r in rs]
        ax = axes[0][col]
        ax.axvspan(30, 42, color="#d9d9d9", alpha=0.8, lw=0)
        ax.plot(t, sc, color=color, lw=1.3)
        ax.set_title(title, fontsize=8)
        ax.set_ylabel("score", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.text(31, ax.get_ylim()[1] * 0.90, "defect", fontsize=6.5, color="#444")
        ax2 = axes[1][col]
        ax2.axvspan(30, 42, color="#d9d9d9", alpha=0.8, lw=0)
        ax2.fill_between(t, 0, mk, step="mid", color=color, alpha=0.55)
        ax2.set_ylim(-0.05, 1.05); ax2.set_yticks([0, 1])
        ax2.set_ylabel("mask", fontsize=7); ax2.set_xlabel("frame index", fontsize=7)
        ax2.tick_params(labelsize=7)
        hit = sum(m for tt, m in zip(t, mk) if 30 <= tt < 42)
        ax2.text(44, 0.72, f"{hit}/12 hit", fontsize=6.5, color="#333")
    fig.tight_layout()
    out = os.path.join(FIG, "fig2_detection_scores.png")
    fig.savefig(out); plt.close(fig)
    print(out)


def fig3():
    rows = read(os.path.join(WS, "results", "runs", "tierA_matrix_v1", "per_sequence.csv"))
    vals = {}
    for m in ("A2", "A3", "A4"):
        rs = [r for r in rows if r["injection"] == "A" and int(r["length"]) == 12 and r["method"] == m]
        vals[m] = (100 * np.mean([float(r["outside_changed_pixel_fraction"]) for r in rs]),
                   np.mean([float(r["boundary_jump_error_sum"]) for r in rs]))
    labels = ["A2\nlocal median-7", "A3\noutside linear k=3", "A4\nfull-seq median-7"]
    colors = ["#999999", "#01665e", "#8c510a"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.5))
    x = np.arange(3)
    axes[0].bar(x, [vals[m][0] for m in ("A2", "A3", "A4")], color=colors, width=0.62)
    axes[0].set_xticks(x); axes[0].set_xticklabels(labels, fontsize=7)
    axes[0].set_ylabel("outside changed pixels (%)")
    axes[0].set_title("(a) outside-interval changes", fontsize=8)
    for i, m in enumerate(("A2", "A3", "A4")):
        axes[0].text(i, vals[m][0] + 0.8, f"{vals[m][0]:.1f}%", ha="center", fontsize=7)
    axes[1].bar(x, [vals[m][1] for m in ("A2", "A3", "A4")], color=colors, width=0.62)
    axes[1].set_xticks(x); axes[1].set_xticklabels(labels, fontsize=7)
    axes[1].set_ylabel("boundary error (sum)")
    axes[1].set_title("(b) boundary error", fontsize=8)
    for i, m in enumerate(("A2", "A3", "A4")):
        axes[1].text(i, vals[m][1] + 0.8, f"{vals[m][1]:.1f}", ha="center", fontsize=7)
    fig.tight_layout()
    out = os.path.join(FIG, "fig3_writeback_scope.png")
    fig.savefig(out); plt.close(fig)
    print(out)


if __name__ == "__main__":
    fig2()
    fig3()
