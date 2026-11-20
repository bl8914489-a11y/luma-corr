"""Build the full 13-sequence method matrix with bootstrap CIs and win counts."""
from __future__ import annotations

import csv
import json
import os

import numpy as np

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "tierA_matrix_v1", "per_sequence.csv")
OUT = os.path.join(WS, "results", "tables")
os.makedirs(OUT, exist_ok=True)
rows = list(csv.DictReader(open(RUN, encoding="utf-8")))
SEQS = sorted({r["sequence"] for r in rows})
METHODS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A7f", "A8", "A9"]
INJS = [("A", "A: offset -20"), ("B", "B: gamma 2.0"), ("B13", "B': gamma 1.3")]
rng = np.random.default_rng(20261121)


def vals(inj, L, m):
    d = {r["sequence"]: float(r["y_mae"]) for r in rows
         if r["injection"] == inj and int(r["length"]) == L and r["method"] == m}
    return np.array([d[s] for s in SEQS])


def ci(a):
    bs = np.array([np.mean(rng.choice(a, len(a), replace=True)) for _ in range(4000)])
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


lines = ["# Full 13-sequence matrix (Y-MAE, lower is better)", "",
         "All 13 sequences, bootstrap 95% CI over sequences (4,000 resamples).", ""]
for inj, label in INJS:
    lines += [f"## {label}", "", "| method | len1 | len4 | len12 |", "|---|---:|---:|---:|"]
    for m in METHODS:
        cells = []
        for L in (1, 4, 12):
            a = vals(inj, L, m); lo, hi = ci(a)
            cells.append(f"{a.mean():.2f} [{lo:.2f},{hi:.2f}]")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines.append("")

lines += ["## Win counts (A7f / A7 / A5 vs A3, per sequence)", "",
          "| injection | len | A7f>A3 | A7>A3 | A5>A3 | A7f<A7 |", "|---|---:|---:|---:|---:|---:|"]
for inj, _ in INJS:
    for L in (1, 4, 12):
        a3, a7, a7f, a5 = vals(inj, L, "A3"), vals(inj, L, "A7"), vals(inj, L, "A7f"), vals(inj, L, "A5")
        lines.append(f"| {inj} | {L} | {int((a7f<a3).sum())}/13 | {int((a7<a3).sum())}/13 | "
                     f"{int((a5<a3).sum())}/13 | {int((a7f<a7).sum())}/13 |")
lines.append("")

# CSV
with open(os.path.join(OUT, "full13_matrix.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["injection", "length", "method", "mean", "ci_low", "ci_high", "sd"])
    for inj, _ in INJS:
        for L in (1, 4, 12):
            for m in METHODS:
                a = vals(inj, L, m); lo, hi = ci(a)
                w.writerow([inj, L, m, round(float(a.mean()), 4), round(lo, 4), round(hi, 4), round(float(a.std(ddof=1)), 4)])
open(os.path.join(WS, "results", "FULL13_MATRIX_2026-11-21.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines[:18]))
print("saved")
