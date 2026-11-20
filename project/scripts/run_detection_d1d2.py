"""Run the RQ3 D1/D2 experiments (novelty-report Section 5).

Outputs per-condition frame/interval metrics, per-condition PR curves, and a
D1 parameter sweep.  Everything is CPU-only and deterministic.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import detect, evaluate_detection  # noqa: E402
from luma_corr.detection_d1 import (d1_score, d2_spans, eq5_mask, frame_metrics_from_mask,  # noqa: E402
                                    hist_stack, interval_metrics, pr_curve, robust_parts, robust_threshold)
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.provenance import (code_tree_sha256, config_sha256, env_info, sha256_file,  # noqa: E402
                                  write_json_atomic)

FIELDS = ["sequence", "injection", "length", "detector", "tp", "fp", "fn", "recall", "precision",
          "iou", "f1", "fp_rate", "interval_iou", "interval_hit", "n_spans", "span_start", "span_end",
          "boundary_err", "ap", "threshold_hi", "threshold_lo"]
PR_FIELDS = ["sequence", "injection", "length", "detector", "threshold", "recall", "precision"]
SWEEP_FIELDS = ["bins", "sigma", "mode", "length", "n_conditions", "recall", "precision", "f1",
                "interval_iou", "ap"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--sequences", default=None)
    ap.add_argument("--lengths", default=None)
    ap.add_argument("--skip-sweep", action="store_true")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg_hash = config_sha256(cfg)
    with open(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    seqs = sorted(manifest["sequences"])
    if args.sequences:
        seqs = [x.strip() for x in args.sequences.split(",") if x.strip()]
    start = int(cfg["start"])
    run_id = args.run_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_rq3d1d2_{cfg_hash[:8]}")
    root = os.path.join(args.workspace, "results", "runs")
    final = os.path.join(root, run_id)
    staging = os.path.join(root, f".staging_{run_id}")
    if os.path.exists(final):
        raise SystemExit(f"refusing to overwrite {final}")
    os.makedirs(staging, exist_ok=True)

    started = time.time()
    write_json_atomic(os.path.join(staging, "run_manifest.json"), {
        "run_id": run_id, "kind": "rq3_d1d2", "config": cfg, "config_sha256": cfg_hash,
        "code_tree_sha256": code_tree_sha256([os.path.join(args.workspace, "project", "src"),
                                              os.path.join(args.workspace, "project", "configs")]),
        "dataset_manifest_sha256": sha256_file(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json")),
        "environment": env_info(), "command": " ".join(sys.argv), "sequences": seqs,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "not_run": {"ffmpeg_filters": "NOT_RUN", "all_in_one_cuda": "NOT_RUN", "blazebvd_network": "NOT_RUN"},
    })

    cf = open(os.path.join(staging, "per_condition.csv"), "w", newline="", encoding="utf-8")
    pf = open(os.path.join(staging, "pr_points.csv"), "w", newline="", encoding="utf-8")
    wc, wp = csv.DictWriter(cf, fieldnames=FIELDS), csv.DictWriter(pf, fieldnames=PR_FIELDS)
    wc.writeheader(); wp.writeheader()

    hist_cache: dict = {}
    luma_cache: dict = {}
    frames_cache: dict = {}

    def get_frames(seq, inj, length):
        key = (seq, inj, length)
        if key not in frames_cache:
            ref = load_frames(os.path.join(args.workspace, "data", "frames", seq))
            if inj == "CLEAN":
                frames_cache[key] = ref
            else:
                spec = next(InjectionSpec.from_dict(d) for d in cfg["injections"] if d["id"] == inj)
                frames_cache[key] = apply_injection(ref, spec, start, length).injected
        return frames_cache[key]

    def get_hist(seq, inj, length, bins):
        key = (seq, inj, length, bins)
        if key not in hist_cache:
            hist_cache[key] = hist_stack(get_frames(seq, inj, length), bins)
        return hist_cache[key]

    def get_luma(seq, inj, length):
        key = (seq, inj, length)
        if key not in luma_cache:
            luma_cache[key] = frame_luma_means(get_frames(seq, inj, length))
        return luma_cache[key]

    n_cond = 0
    for seq in seqs:
        for injd in cfg["injections"]:
            inj_id = injd["id"]
            lengths = [0] if inj_id == "CLEAN" else cfg["lengths"]
            if args.lengths and inj_id != "CLEAN":
                lengths = [int(x) for x in args.lengths.split(",")]
            for length in lengths:
                frames = get_frames(seq, inj_id, length)
                luma_means = get_luma(seq, inj_id, length)
                for det in cfg["detectors"]:
                    kind = det["kind"]
                    if kind == "median_dev":
                        res = detect(frames, {"id": det["id"], "kind": "median_dev",
                                              "window": det.get("window", 7),
                                              "threshold": det.get("threshold", 1.0)})
                        ev = evaluate_detection(res, start, length)
                        mask, score = res["mask"], res["score"]
                        hi = ev["threshold_hi"]; lo = ev["threshold_lo"]
                        spans = ev["detected_spans"]; ap = float("nan")
                    elif kind == "cusum":
                        res = detect(frames, {"id": det["id"], "kind": "hist_kl_cusum",
                                              "bins": det["bins"], "window": det.get("window", 41),
                                              "smooth": det.get("smooth", 3), "k": det.get("k", 0.5),
                                              "h": det.get("h", 6.0), "min_len": det.get("min_len", 2)})
                        ev = evaluate_detection(res, start, length)
                        mask, score = res["mask"], res["score"]
                        hi = ev["threshold_hi"]; lo = ev["threshold_lo"]
                        spans = ev["detected_spans"]; ap = float("nan")
                    else:
                        H = get_hist(seq, inj_id, length, int(det.get("bins", 64)))
                        score = d1_score(H, float(det.get("sigma", 2.0)), det.get("mode", "js"))
                        if kind == "eq5":
                            mask = eq5_mask(score, int(det.get("neighbors", 5)), float(det.get("alpha", 1.0)))
                            hi = float("nan"); lo = float("nan")
                            spans = []
                            idx = np.nonzero(mask)[0]
                            if len(idx):
                                a = idx[0]
                                for i in range(1, len(idx)):
                                    if idx[i] != idx[i - 1] + 1:
                                        spans.append((int(a), int(idx[i - 1]) + 1)); a = idx[i]
                                spans.append((int(a), int(idx[-1]) + 1))
                        elif kind == "d1":
                            hi = robust_threshold(score, float(det.get("k", 3.0)))
                            lo = hi
                            mask = score > hi
                            spans = []
                            idx = np.nonzero(mask)[0]
                            if len(idx):
                                a = idx[0]
                                for i in range(1, len(idx)):
                                    if idx[i] != idx[i - 1] + 1:
                                        spans.append((int(a), int(idx[i - 1]) + 1)); a = idx[i]
                                spans.append((int(a), int(idx[-1]) + 1))
                        elif kind == "d2":
                            hi, med = robust_parts(score, float(det.get("k", 3.0)))
                            lo = med + float(det.get("lo_ratio", 0.5)) * (hi - med)
                            spans = d2_spans(score, hi, lo, luma_means,
                                             min_len=int(det.get("min_len", 2)),
                                             max_gap=int(det.get("max_gap", 2)),
                                             expand=bool(det.get("expand", True)),
                                             refine=bool(det.get("refine", True)))
                            mask = np.zeros(len(score), dtype=bool)
                            for a, b in spans:
                                mask[a:b] = True
                        else:
                            raise ValueError(kind)
                        if length > 0:
                            _, ap = pr_curve(score, start, length, 40)
                        else:
                            ap = float("nan")
                    fm = frame_metrics_from_mask(mask, start, length)
                    im = interval_metrics(spans, start, length)
                    wc.writerow({
                        "sequence": seq, "injection": inj_id, "length": length, "detector": det["id"],
                        **fm, **im, "ap": ap, "threshold_hi": hi, "threshold_lo": lo,
                    })
                    if length > 0 and kind != "median_dev" and kind != "cusum":
                        pts, _ = pr_curve(score, start, length, 20)
                        for thr, r, p in pts:
                            wp.writerow({"sequence": seq, "injection": inj_id, "length": length,
                                         "detector": det["id"], "threshold": thr,
                                         "recall": r, "precision": p})
                    n_cond += 1
                    if n_cond % 100 == 0:
                        print(f"[{n_cond}] {seq} {inj_id} len={length} {det['id']}", flush=True)
    cf.close(); pf.close()

    # ---- D1 parameter sweep (len=12 only) ----
    sw = {} if args.skip_sweep else cfg.get("sweep", {})
    sweep_rows = []
    if sw:
        for bins in sw["bins"]:
            for sigma in sw["sigmas"]:
                for mode in sw["modes"]:
                    for length in sw["lengths"]:
                        agg = []
                        for seq in seqs:
                            for injd in cfg["injections"]:
                                if injd["id"] == "CLEAN":
                                    continue
                                H = get_hist(seq, injd["id"], length, bins)
                                score = d1_score(H, sigma, mode)
                                hi, med = robust_parts(score, 3.0)
                                lo = med + 0.5 * (hi - med)
                                spans = d2_spans(score, hi, lo, get_luma(seq, injd["id"], length),
                                                 min_len=2, max_gap=2)
                                mask = np.zeros(len(score), dtype=bool)
                                for a, b in spans:
                                    mask[a:b] = True
                                fm = frame_metrics_from_mask(mask, start, length)
                                im = interval_metrics(spans, start, length)
                                _, ap = pr_curve(score, start, length, 30)
                                agg.append((fm["recall"], fm["precision"], fm["f1"], im["interval_iou"], ap))
                        a = np.array(agg, dtype=float)
                        sweep_rows.append({
                            "bins": bins, "sigma": sigma, "mode": mode, "length": length,
                            "n_conditions": len(agg),
                            "recall": float(np.mean(a[:, 0])), "precision": float(np.mean(a[:, 1])),
                            "f1": float(np.mean(a[:, 2])), "interval_iou": float(np.nanmean(a[:, 3])),
                            "ap": float(np.nanmean(a[:, 4])),
                        })
                        print("sweep", bins, sigma, mode, sweep_rows[-1], flush=True)
        with open(os.path.join(staging, "sweep.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=SWEEP_FIELDS); w.writeheader(); w.writerows(sweep_rows)

    artifacts = {f: {"sha256": sha256_file(os.path.join(staging, f)),
                     "bytes": os.path.getsize(os.path.join(staging, f))}
                 for f in os.listdir(staging) if f.endswith(".csv")}
    summary = {"run_id": run_id, "status": "SUCCESS", "n_conditions": n_cond,
               "wall_seconds": time.time() - started, "artifacts": artifacts,
               "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(staging, "summary.json"), summary)
    os.rename(staging, final)
    print("DONE", final, "conditions", n_cond)


if __name__ == "__main__":
    main()
