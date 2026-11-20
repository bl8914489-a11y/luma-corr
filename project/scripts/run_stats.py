"""Statistics for the Tier A matrix.

Produces:
* RQ1 method summary with cluster bootstrap 95% intervals over the 13 videos;
* pairwise A3-vs-baseline tests on per-frame errors and per-video means;
* RQ2 preservation/boundary summary and paired A3-vs-A4 tests.

Frame-level Wilcoxon p-values are descriptive (frames within a video are not
independent); the video-level test and cluster bootstrap are the inferential
results.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.provenance import sha256_file, write_json_atomic  # noqa: E402
from luma_corr.stats import (bootstrap_mean_ci, cluster_bootstrap, holm,  # noqa: E402
                             wilcoxon_signed_rank)

METRICS = ["y_mae", "rgb_mae", "psnr", "ssim", "hist_dist"]
OUT_METRICS = ["outside_changed_pixel_fraction", "outside_rgb_mae", "outside_y_mae",
               "boundary_jump_error_sum", "boundary_estimator_bias", "boundary_outside_jump",
               "flicker_first_diff_var", "flicker_second_diff_rms"]


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--proposed", default="A3")
    args = ap.parse_args()

    seq_rows = list(csv.DictReader(open(os.path.join(args.run_dir, "per_sequence.csv"), encoding="utf-8")))
    frame_rows = list(csv.DictReader(open(os.path.join(args.run_dir, "per_frame.csv"), encoding="utf-8")))

    injections = sorted({r["injection"] for r in seq_rows})
    lengths = sorted({int(r["length"]) for r in seq_rows})
    methods = sorted({r["method"] for r in seq_rows})
    sequences = sorted({r["sequence"] for r in seq_rows})
    os.makedirs(args.out, exist_ok=True)

    # ---------- RQ1 summary ----------
    rq1 = []
    by = defaultdict(list)
    for r in seq_rows:
        by[(r["injection"], int(r["length"]), r["method"])].append(r)
    for inj in injections:
        for length in lengths:
            for m in methods:
                rs = by[(inj, length, m)]
                row = {"injection": inj, "length": length, "method": m, "n_sequences": len(rs)}
                for metric in METRICS:
                    vals = np.array([fnum(x[metric]) for x in rs], dtype=float)
                    vals = vals[np.isfinite(vals)]
                    bs = bootstrap_mean_ci(vals)
                    row[f"{metric}_mean"] = bs["mean"]
                    row[f"{metric}_ci_low"] = bs["ci_low"]
                    row[f"{metric}_ci_high"] = bs["ci_high"]
                for metric in OUT_METRICS:
                    vals = np.array([fnum(x[metric]) for x in rs], dtype=float)
                    vals = vals[np.isfinite(vals)]
                    bs = bootstrap_mean_ci(vals)
                    row[f"{metric}_mean"] = bs["mean"]
                    row[f"{metric}_ci_low"] = bs["ci_low"]
                    row[f"{metric}_ci_high"] = bs["ci_high"]
                row["correction_clip_fraction_mean"] = float(
                    np.mean([fnum(x["correction_clip_fraction"]) or 0.0 for x in rs]))
                rq1.append(row)
    with open(os.path.join(args.out, "rq1_method_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rq1[0]))
        w.writeheader()
        w.writerows(rq1)

    # ---------- pairwise tests ----------
    # per-frame y_mae for interval frames
    pf = defaultdict(dict)
    for r in frame_rows:
        if r["in_interval"] != "1":
            continue
        key = (r["sequence"], r["injection"], int(r["length"]), int(r["t"]))
        pf[key][r["method"]] = fnum(r["y_mae"])

    pairwise = []
    pvals = []
    for inj in injections:
        for length in lengths:
            for m in methods:
                if m == args.proposed:
                    continue
                # frame level
                diffs = []
                for (seq, i, L, t), vals in pf.items():
                    if i != inj or L != length:
                        continue
                    a, b = vals.get(args.proposed), vals.get(m)
                    if a is not None and b is not None:
                        diffs.append(a - b)
                fr = wilcoxon_signed_rank(np.array(diffs))
                per_video = defaultdict(list)
                for (seq, i, L, t), vals in pf.items():
                    if i == inj and L == length:
                        a, b = vals.get(args.proposed), vals.get(m)
                        if a is not None and b is not None:
                            per_video[seq].append(a - b)
                vd = np.array([np.mean(v) for v in per_video.values()])
                vr = wilcoxon_signed_rank(vd)
                cb = cluster_bootstrap(vd)
                rec = {
                    "injection": inj, "length": length, "method_a": args.proposed, "method_b": m,
                    "n_frames": fr["n"], "frame_wilcoxon_p": fr["p"], "frame_rank_biserial": fr["rank_biserial"],
                    "n_videos": vr["n"], "video_wilcoxon_p": vr["p"], "video_rank_biserial": vr["rank_biserial"],
                    "video_median_diff": cb["median_diff"], "video_mean_diff": cb["mean_diff"],
                    "video_ci_low": cb["ci_low"], "video_ci_high": cb["ci_high"],
                }
                pairwise.append(rec)
                pvals.append(vr["p"])
    for rec, p in zip(pairwise, holm(pvals)):
        rec["video_p_holm"] = p
    with open(os.path.join(args.out, "rq1_pairwise.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pairwise[0]))
        w.writeheader()
        w.writerows(pairwise)

    # ---------- RQ2: proposed vs full-sequence A4 ----------
    rq2 = []
    for inj in injections:
        for length in lengths:
            for m in methods:
                rs = by[(inj, length, m)]
                rec = {"injection": inj, "length": length, "method": m}
                for metric in ["outside_changed_pixel_fraction", "outside_rgb_mae",
                               "boundary_jump_error_sum", "boundary_estimator_bias",
                               "boundary_outside_jump", "flicker_first_diff_var"]:
                    vals = np.array([fnum(x[metric]) for x in rs], dtype=float)
                    bs = bootstrap_mean_ci(vals[np.isfinite(vals)])
                    rec[metric + "_mean"] = bs["mean"]
                    rec[metric + "_ci_low"] = bs["ci_low"]
                    rec[metric + "_ci_high"] = bs["ci_high"]
                rq2.append(rec)
    with open(os.path.join(args.out, "rq2_preservation.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rq2[0]))
        w.writeheader()
        w.writerows(rq2)

    a, b = args.proposed, "A4"
    rq2_pair = []
    for inj in injections:
        for length in lengths:
            for metric in ["outside_changed_pixel_fraction", "outside_rgb_mae", "boundary_jump_error_sum"]:
                va = np.array([fnum(x[metric]) for x in by[(inj, length, a)]], dtype=float)
                vb = np.array([fnum(x[metric]) for x in by[(inj, length, b)]], dtype=float)
                d = va - vb
                ok = np.isfinite(d)
                d = d[ok]
                if len(d) == 0:
                    continue
                wr = wilcoxon_signed_rank(d)
                cb = cluster_bootstrap(d)
                rq2_pair.append({"injection": inj, "length": length, "metric": metric,
                                 "n_videos": len(d), "mean_diff": cb["mean_diff"],
                                 "ci_low": cb["ci_low"], "ci_high": cb["ci_high"],
                                 "wilcoxon_p": wr["p"], "rank_biserial": wr["rank_biserial"]})
    with open(os.path.join(args.out, "rq2_pairwise.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rq2_pair[0]))
        w.writeheader()
        w.writerows(rq2_pair)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_run": os.path.abspath(args.run_dir),
        "source_hashes": {f: sha256_file(os.path.join(args.run_dir, f))
                          for f in ("per_frame.csv", "per_sequence.csv")},
        "n_sequences": len(sequences), "proposed": args.proposed,
        "outputs": {f: sha256_file(os.path.join(args.out, f)) for f in
                    ("rq1_method_summary.csv", "rq1_pairwise.csv", "rq2_preservation.csv", "rq2_pairwise.csv")},
    }
    write_json_atomic(os.path.join(args.out, "stats_manifest.json"), summary)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
