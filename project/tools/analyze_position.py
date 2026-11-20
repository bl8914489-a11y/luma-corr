"""Analyse interval-position sensitivity and draw the figure."""
from __future__ import annotations

import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

WS = r"F:\周四焜哥论文"
RUNS = {10: "position_start10_v1", 30: "tierA_matrix_v1", 50: "position_start50_v1"}
OUT = os.path.join(WS, "results", "POSITION_2026-11-18.md")
FIG = os.path.join(WS, "paper", "figures", "fig5_position.png")
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 300, "savefig.bbox": "tight"})


def read(run):
    p = os.path.join(WS, "results", "runs", run, "per_sequence.csv")
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def val(rows, inj, m, start):
    v = [float(r["y_mae"]) for r in rows if r["injection"] == inj and int(r["length"]) == 12
         and r["method"] == m and int(r["start"]) == start]
    return float(np.mean(v))


def main():
    data = {s: read(r) for s, r in RUNS.items()}
    lines = ["# Interval-position sensitivity (2026-11-18)", "",
             "13 sequences, len12, Y MAE; starts 10/30/50 (interval [s,s+12)).", ""]
    for inj in ("A", "B", "B13"):
        lines += [f"## {inj}", "| start | A3 | A7 |", "|---|---|---|"]
        for s in (10, 30, 50):
            lines.append(f"| {s} | {val(data[s], inj, 'A3', s):.2f} | {val(data[s], inj, 'A7', s):.2f} |")
        lines.append("")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.5))
    for ax, inj, title in [(axes[0], "A", "(a) offset -20"), (axes[1], "B", "(b) gamma 2.0")]:
        for m, c in (("A3", "#01665e"), ("A7", "#8c510a")):
            ys = [val(data[s], inj, m, s) for s in (10, 30, 50)]
            ax.plot([10, 30, 50], ys, "o-", color=c, label=m, lw=1.3, ms=4)
        ax.set_xticks([10, 30, 50]); ax.set_xlabel("interval start")
        ax.set_ylabel("interval Y MAE"); ax.set_title(title, fontsize=8)
        ax.legend(frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig(FIG); plt.close(fig)
    print("wrote", OUT, FIG)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
