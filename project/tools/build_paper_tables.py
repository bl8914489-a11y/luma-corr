"""Generate LaTeX (booktabs) tables for the paper from run artifacts."""
from __future__ import annotations

import csv
import json
import os

import numpy as np

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT = os.path.join(WS, "paper", "tables")
os.makedirs(OUT, exist_ok=True)
DEV = {"sailboat", "book", "horse"}
METHODS = [
    ("A1", "No-op"), ("A2", "Local median-7"), ("A3", "Outside linear $k{=}3$"),
    ("A4", "Full-sequence median-7"), ("A5", "STE hist. spec."), ("A6", "CLAHE"),
    ("A7", "Adaptive gamma"), ("A7f", "Fixed inverse $\\gamma{=}2$"),
    ("A8", "Temporal bilateral"), ("A9", "Kalman/RTS"),
]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def dev_mean(rows, inj, L, m, key="y_mae"):
    v = [float(r[key]) for r in rows if r["injection"] == inj and int(r["length"]) == L
         and r["method"] == m and r["sequence"] in DEV]
    return float(np.mean(v))


def main():
    mat = read(os.path.join(WS, "results", "runs", "tierA_matrix_v1", "per_sequence.csv"))

    # ---- RQ1: dev-3 Y MAE, three injections ----
    lines = [r"\begin{table*}[t]", r"\centering", r"\small",
             r"\caption{Interval Y MAE on the three development sequences (lower is better).}",
             r"\label{tab:rq1}", r"\begin{tabular}{lrrrrrrrrr}", r"\toprule",
             r" & \multicolumn{3}{c}{A ($-20$)} & \multicolumn{3}{c}{B ($\gamma{=}2$)} & \multicolumn{3}{c}{B$'$ ($\gamma{=}1.3$)} \\",
             r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}\cmidrule(lr){8-10}",
             r"Method & 1 & 4 & 12 & 1 & 4 & 12 & 1 & 4 & 12 \\", r"\midrule"]
    for m, label in METHODS:
        vals = [dev_mean(mat, inj, L, m) for inj in ("A", "B", "B13") for L in (1, 4, 12)]
        lines.append(label + " & " + " & ".join(f"{v:.2f}" for v in vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    open(os.path.join(OUT, "rq1.tex"), "w", encoding="utf-8").write("\n".join(lines))

    # ---- RQ2: preservation ----
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             r"\caption{Outside-interval preservation and boundary error (13 sequences, A injection).}",
             r"\label{tab:rq2}", r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Method & OutFrac $\downarrow$ & Outside RGB MAE $\downarrow$ & Boundary $\downarrow$ & Bias \\", r"\midrule"]
    for m, label in [("A2", "Local median-7"), ("A3", "Outside linear $k{=}3$"), ("A4", "Full-seq median-7")]:
        def mm(key):
            return float(np.mean([float(r[key]) for r in mat if r["injection"] == "A"
                                  and int(r["length"]) == 12 and r["method"] == m]))
        lines.append(f"{label} & {100*mm('outside_changed_pixel_fraction'):.2f}\\% & "
                     f"{mm('outside_rgb_mae'):.2f} & {mm('boundary_jump_error_sum'):.2f} & "
                     f"{mm('boundary_estimator_bias'):.2f} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    open(os.path.join(OUT, "rq2.tex"), "w", encoding="utf-8").write("\n".join(lines))

    # ---- RQ3: detection ----
    det = read(os.path.join(WS, "results", "runs", "rq3_detection_v2", "per_condition.csv"))
    def dm(det_id, L, key):
        return float(np.mean([float(r[key]) for r in det if r["detector"] == det_id
                              and int(r["length"]) == L and r["injection"] != "CLEAN"]))
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             r"\caption{Detection: frame-level recall/precision, mean over 13 sequences and 3 injections.}",
             r"\label{tab:rq3}", r"\begin{tabular}{lrrrrrr}", r"\toprule",
             r"Detector & R@1 & P@1 & R@4 & P@4 & R@12 & P@12 \\", r"\midrule"]
    for det_id, label in [("median_dev", "Local median deviation"),
                          (r"hist_kl", r"Global-hist.\ JS + hysteresis"),
                          (r"hist_kl_cusum", r"Rolling-hist.\ JS + CUSUM")]:
        lines.append(label + " & " + " & ".join(
            f"{dm(det_id, L, 'recall'):.3f} & {dm(det_id, L, 'precision'):.3f}" for L in (1, 4, 12)) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    open(os.path.join(OUT, "rq3.tex"), "w", encoding="utf-8").write("\n".join(lines))

    # ---- B2 ----
    b2rows = read(os.path.join(WS, "results", "runs", "b2_len12_v1", "per_case.csv"))
    def bm(inj, m, key):
        v = [float(r[key]) for r in b2rows if r["injection"] == inj and r["method"] == m]
        return float(np.mean(v))
    def ba(m, key):
        v = [float(r[key]) for r in b2rows if r["method"] == m]
        return float(np.mean(v))
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             r"\caption{Deep blind baseline (All-In-One, CVPR 2023) vs local write-back on 39 balanced injected cases (13 sequences $\times$ 3 injections, len12).}",
             r"\label{tab:b2}", r"\begin{tabular}{lrrrrrrr}", r"\toprule",
             r"Method & A & B & B$'$ & Overall & OutFrac & Outside RGB & Boundary \\", r"\midrule"]
    for key, label in [("noop", "No-op"), ("A3", "A3 local"), ("B2_all_in_one", "B2 All-In-One")]:
        lines.append(f"{label} & {bm('A',key,'y_mae'):.2f} & {bm('B',key,'y_mae'):.2f} & {bm('B13',key,'y_mae'):.2f} & "
                     f"{ba(key,'y_mae'):.2f} & {100*ba(key,'outfrac'):.2f}\\% & {ba(key,'outside_rgb_mae'):.2f} & {ba(key,'boundary'):.2f} " + " \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    open(os.path.join(OUT, "b2.tex"), "w", encoding="utf-8").write("\n".join(lines))

    # ---- ablation k ----
    ctx = read(os.path.join(WS, "results", "runs", "ablation_context_v1", "per_sequence.csv"))
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             r"\caption{Context-window ablation for the proposed offset estimator (mean over 13 sequences).}",
             r"\label{tab:k}", r"\begin{tabular}{lrrrrrr}", r"\toprule",
             r" & \multicolumn{3}{c}{A} & \multicolumn{3}{c}{B ($\gamma{=}2$)} \\",
             r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
             r"$k$ & 1 & 4 & 12 & 1 & 4 & 12 \\", r"\midrule"]
    for k, label in [("k1", "1"), ("k3", "3"), ("k5", "5")]:
        vals = []
        for inj in ("A", "B"):
            for L in (1, 4, 12):
                v = [float(r["y_mae"]) for r in ctx if r["method"] == k and r["injection"] == inj
                     and int(r["length"]) == L]
                vals.append(float(np.mean(v)))
        lines.append(label + " & " + " & ".join(f"{v:.2f}" for v in vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    open(os.path.join(OUT, "ablation_k.tex"), "w", encoding="utf-8").write("\n".join(lines))

    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# LaTeX tables\n\nGenerated from run CSVs; do not edit by hand.\n\n"
                 "`rq1.tex` / `rq2.tex` / `rq3.tex` / `b2.tex` / `ablation_k.tex`.\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
