"""Analyse injection-strength sensitivity and draw the two-panel figure."""
from __future__ import annotations

import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "sensitivity_v1")
OUT = os.path.join(WS, "results", "SENSITIVITY_2026-11-18.md")
FIG = os.path.join(WS, "paper", "figures", "fig4_sensitivity.png")
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 300, "savefig.bbox": "tight"})


def read(name):
    with open(os.path.join(RUN, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def mean(rows, **kw):
    v = [float(r["y_mae"]) for r in rows if all(r[k] == str(v) for k, v in kw.items())]
    return float(np.mean(v)) if v else float("nan")


def main():
    rows = read("per_sequence.csv")
    inj_order = ["A10", "A20", "A30", "B13", "B15", "B20", "B25"]
    methods = ["A1", "A2", "A3", "A7"]
    lines = ["# Injection-strength sensitivity (2026-11-18)", "",
             "13 sequences, interval [30,42), Y MAE (lower is better).", "",
             "| injection | " + " | ".join(methods) + " |", "|---|" + "---|" * len(methods)]
    for inj in inj_order:
        lines.append("| " + inj + " | " + " | ".join(f"{mean(rows, injection=inj, length=12, method=m):.2f}"
                                                     for m in methods) + " |")
    # clipping for A3/A7 at len12
    lines += ["", "## Clipping fraction at len12 (%)", "",
              "| injection | A3 | A7 |", "|---|---|---|"]
    for inj in inj_order:
        vals = []
        for m in ("A3", "A7"):
            v = [100 * float(r["correction_clip_fraction"]) for r in rows
                 if r["injection"] == inj and int(r["length"]) == 12 and r["method"] == m]
            vals.append(float(np.mean(v)) if v else float("nan"))
        lines.append(f"| {inj} | {vals[0]:.2f} | {vals[1]:.2f} |")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    off = [10, 20, 30]
    for m, c in (("A2", "#999999"), ("A3", "#01665e"), ("A7", "#8c510a")):
        ys = [mean(rows, injection=f"A{x}", length=12, method=m) for x in off]
        axes[0].plot(off, ys, "o-", color=c, label=m, lw=1.3, ms=4)
    axes[0].set_xlabel("offset magnitude (code values)")
    axes[0].set_ylabel("interval Y MAE")
    axes[0].set_title("(a) constant offset", fontsize=8)
    axes[0].set_xticks(off); axes[0].legend(frameon=False, fontsize=7)
    gam = [1.3, 1.5, 2.0, 2.5]
    for m, c in (("A1", "#999999"), ("A3", "#01665e"), ("A7", "#8c510a")):
        ys = [mean(rows, injection=f"B{int(g*10):02d}" if g != 2.0 else "B20", length=12, method=m) for g in gam]
        axes[1].plot(gam, ys, "o-", color=c, label=m, lw=1.3, ms=4)
    axes[1].set_xlabel("gamma value")
    axes[1].set_ylabel("interval Y MAE")
    axes[1].set_title("(b) gamma transform", fontsize=8)
    axes[1].set_xticks(gam); axes[1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG); plt.close(fig)
    print("wrote", OUT, FIG)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
