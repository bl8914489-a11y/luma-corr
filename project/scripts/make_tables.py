"""Build the camera-ready result tables from the recorded runs.

Every number is read from a run directory produced by the experiment scripts;
nothing is typed by hand.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.stats import bootstrap_mean_ci  # noqa: E402

DEV = {"sailboat", "book", "horse"}
METHOD_ORDER = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A7f", "A8", "A9"]
METHOD_LABEL = {
    "A1": "No-op", "A2": "Local 7-frame median", "A3": "Outside linear k=3 (proposed)",
    "A4": "Full-sequence 7-frame median", "A5": "Scale-time equalisation",
    "A6": "CLAHE", "A7": "Adaptive gamma", "A7f": "Fixed inverse gamma 2",
    "A8": "Temporal bilateral", "A9": "Kalman/RTS luma", "k1": "k=1", "k3": "k=3 (proposed)",
    "k5": "k=5", "hard": "Hard clip", "soft": "Tanh shoulder 235",
}


def read_csv(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def mean_ci(vals):
    v = np.array([x for x in vals if np.isfinite(x)], dtype=float)
    return bootstrap_mean_ci(v)


def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def md_table(rows, cols, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--matrix", default="tierA_matrix_v1")
    ap.add_argument("--detection", default="rq3_detection_v2")
    ap.add_argument("--context", default="ablation_context_v1")
    ap.add_argument("--clip", default="ablation_clip_v1")
    ap.add_argument("--out", default="results/tables/final")
    args = ap.parse_args()
    root = os.path.join(args.workspace, "results", "runs")
    out = os.path.join(args.workspace, args.out)
    os.makedirs(out, exist_ok=True)
    md = []

    # ---------------- RQ1 ----------------
    seq_rows = read_csv(os.path.join(root, args.matrix, "per_sequence.csv"))
    rq1 = []
    for inj in ["A", "B", "B13"]:
        for length in [1, 4, 12]:
            for m in METHOD_ORDER:
                rs = [r for r in seq_rows if r["injection"] == inj
                      and int(r["length"]) == length and r["method"] == m]
                if not rs:
                    continue
                dev = [r for r in rs if r["sequence"] in DEV]
                allv = mean_ci([f(r["y_mae"]) for r in rs])
                devm = mean_ci([f(r["y_mae"]) for r in dev])
                rq1.append({
                    "injection": inj, "length": length, "method": m, "label": METHOD_LABEL[m],
                    "dev3_y_mae": round(devm["mean"], 3),
                    "dev3_ci": f"[{devm['ci_low']:.2f}, {devm['ci_high']:.2f}]",
                    "all13_y_mae": round(allv["mean"], 3),
                    "all13_ci": f"[{allv['ci_low']:.2f}, {allv['ci_high']:.2f}]",
                    "psnr": round(float(np.mean([f(r["psnr"]) for r in rs])), 2),
                    "ssim": round(float(np.mean([f(r["ssim"]) for r in rs])), 3),
                    "clip_pct": round(100 * float(np.mean([f(r["correction_clip_fraction"]) for r in rs])), 2),
                })
    write_csv(os.path.join(out, "T1_rq1_interval.csv"), rq1)
    for inj in ["A", "B", "B13"]:
        rows = [r for r in rq1 if r["injection"] == inj]
        md.append(f"\n### RQ1 — injection {inj} (Y MAE, dev-3 mean [cluster 95% CI]; all-13 mean)\n")
        md.append(md_table(rows, ["length", "method", "dev3_y_mae", "dev3_ci", "all13_y_mae", "psnr", "ssim", "clip_pct"],
                           ["len", "method", "dev3 Y MAE", "dev3 CI", "all13 Y MAE", "PSNR", "SSIM", "clip %"]))

    # ---------------- RQ2 ----------------
    rq2 = []
    for inj in ["A", "B", "B13"]:
        for length in [1, 4, 12]:
            for m in ["A2", "A3", "A4"]:
                rs = [r for r in seq_rows if r["injection"] == inj and int(r["length"]) == length and r["method"] == m]
                if not rs:
                    continue
                rq2.append({
                    "injection": inj, "length": length, "method": m, "label": METHOD_LABEL[m],
                    "outFrac_pct": round(100 * float(np.mean([f(r["outside_changed_pixel_fraction"]) for r in rs])), 2),
                    "outside_rgb_mae": round(float(np.mean([f(r["outside_rgb_mae"]) for r in rs])), 4),
                    "boundary_total": round(float(np.mean([f(r["boundary_jump_error_sum"]) for r in rs])), 3),
                    "estimator_bias": round(float(np.mean([f(r["boundary_estimator_bias"]) for r in rs])), 3),
                    "outside_jump": round(float(np.mean([f(r["boundary_outside_jump"]) for r in rs])), 3),
                })
    write_csv(os.path.join(out, "T2_rq2_preservation.csv"), rq2)
    md.append("\n### RQ2 — outside preservation and boundary error (all 13 videos)\n")
    md.append(md_table(rq2, ["injection", "length", "method", "outFrac_pct", "outside_rgb_mae", "boundary_total",
                             "estimator_bias", "outside_jump"],
                       ["inj", "len", "method", "outside changed %", "outside RGB MAE", "boundary total",
                        "estimator bias", "outside jump"]))

    # ---------------- RQ3 ----------------
    det = read_csv(os.path.join(root, args.detection, "per_condition.csv"))
    rq3 = []
    for det_id in ["median_dev", "hist_kl", "hist_kl_cusum"]:
        for length in [1, 4, 12]:
            rs = [r for r in det if r["detector"] == det_id and r["injection"] != "CLEAN" and int(r["length"]) == length]
            if not rs:
                continue
            rq3.append({
                "detector": det_id, "length": length,
                "recall": round(float(np.mean([f(r["recall"]) for r in rs])), 3),
                "precision": round(float(np.mean([f(r["precision"]) for r in rs])), 3),
                "iou": round(float(np.mean([f(r["iou"]) for r in rs])), 3),
                "f1": round(float(np.mean([f(r["f1"]) for r in rs])), 3),
                "boundary_err": round(float(np.nanmean([f(r["boundary_abs_error_mean"]) for r in rs])), 2),
            })
    fp = {}
    for det_id in ["median_dev", "hist_kl", "hist_kl_cusum"]:
        rs = [r for r in det if r["detector"] == det_id and r["injection"] == "CLEAN"]
        fp[det_id] = round(float(np.mean([f(r["fp_rate"]) for r in rs])), 3)
    write_csv(os.path.join(out, "T3_rq3_detection.csv"), rq3)
    md.append("\n### RQ3 — detection (mean over 13 videos x 3 injections)\n")
    md.append(md_table(rq3, ["detector", "length", "recall", "precision", "iou", "f1", "boundary_err"],
                       ["detector", "len", "recall", "precision", "IoU", "F1", "boundary err"]))
    md.append("\nClean-sequence false-positive frame rate: " +
              ", ".join(f"{k}={v:.3f}" for k, v in fp.items()) + "\n")

    # ---------------- ablations ----------------
    for tag, run_id, order in [("context", args.context, ["k1", "k3", "k5"]),
                               ("clip", args.clip, ["hard", "soft"])]:
        path = os.path.join(root, run_id, "per_sequence.csv")
        if not os.path.exists(path):
            md.append(f"\n_Ablation `{tag}` not available._\n")
            continue
        rows = read_csv(path)
        tab = []
        for inj in ["A", "B", "B13"]:
            for length in [1, 4, 12]:
                for m in order:
                    rs = [r for r in rows if r["injection"] == inj and int(r["length"]) == length and r["method"] == m]
                    if not rs:
                        continue
                    tab.append({
                        "injection": inj, "length": length, "method": m, "label": METHOD_LABEL.get(m, m),
                        "y_mae": round(float(np.mean([f(r["y_mae"]) for r in rs])), 3),
                        "boundary": round(float(np.mean([f(r["boundary_jump_error_sum"]) for r in rs])), 3),
                        "clip_pct": round(100 * float(np.mean([f(r["correction_clip_fraction"]) for r in rs])), 2),
                        "psnr": round(float(np.mean([f(r["psnr"]) for r in rs])), 2),
                    })
        write_csv(os.path.join(out, f"T4_ablation_{tag}.csv"), tab)
        md.append(f"\n### Ablation — {tag}\n")
        md.append(md_table(tab, ["injection", "length", "method", "y_mae", "boundary", "clip_pct", "psnr"],
                           ["inj", "len", "method", "Y MAE", "boundary", "clip %", "PSNR"]))

    # ---------------- stats ----------------
    stats_dir = os.path.join(args.workspace, "results", "tables", args.matrix)
    pair_path = os.path.join(stats_dir, "rq1_pairwise.csv")
    if os.path.exists(pair_path):
        pair = read_csv(pair_path)
        keep = []
        for r in pair:
            keep.append({
                "injection": r["injection"], "length": r["length"], "baseline": r["method_b"],
                "median_diff": round(f(r["video_median_diff"]), 3),
                "ci": f"[{f(r['video_ci_low']):.2f}, {f(r['video_ci_high']):.2f}]",
                "p_holm": f"{f(r['video_p_holm']):.2g}", "r_rb": round(f(r["video_rank_biserial"]), 2),
                "frame_p": f"{f(r['frame_wilcoxon_p']):.2g}",
            })
        write_csv(os.path.join(out, "T5_stats_A3_vs_baselines.csv"), keep)
        md.append("\n### Paired tests — proposed A3 vs each baseline (negative difference = A3 lower Y MAE)\n")
        md.append(md_table(keep, ["injection", "length", "baseline", "median_diff", "ci", "p_holm", "r_rb"],
                           ["inj", "len", "baseline", "median diff", "95% CI", "Holm p", "rank-biserial"]))

    header = ("# Tier A results (generated from run artifacts)\n\n"
              f"Source run: `{args.matrix}`; detection: `{args.detection}`. "
              "All values are recomputed from `per_sequence.csv` / `per_detection.csv`.\n")
    with open(os.path.join(out, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write(header + "\n".join(md) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
