"""Run the Tier A correction matrix and write per-frame / per-condition tables.

Writes into a staging directory and atomically renames it when complete.  Every
run records the config hash, code-tree hash, environment, dataset manifest hash
and SHA-256 of each produced artifact.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec  # noqa: E402
from luma_corr.pipeline import run_condition  # noqa: E402
from luma_corr.provenance import (code_tree_sha256, config_sha256, env_info, sha256_file,  # noqa: E402
                                  write_json_atomic)

PER_FRAME_FIELDS = ["sequence", "injection", "length", "method", "scope", "t", "in_interval",
                    "y_mae", "rgb_mae", "psnr", "ssim", "hist_dist", "luma_out", "luma_ref",
                    "changed_pixels"]
SUMMARY_FIELDS = ["sequence", "injection", "length", "method", "scope", "start", "end", "frames",
                  "y_mae", "rgb_mae", "psnr", "ssim", "hist_dist",
                  "injection_clip_fraction", "injection_mean_abs_diff",
                  "correction_clip_fraction", "correction_offset_mean", "target_kind",
                  "injected_interval_sha256", "corrected_interval_sha256", "runtime_s",
                  "outside_changed_pixel_fraction", "outside_rgb_mae", "outside_y_mae",
                  "boundary_jump_error_sum", "boundary_left_error", "boundary_right_error",
                  "boundary_estimator_bias", "boundary_outside_jump",
                  "flicker_first_diff_var", "flicker_second_diff_rms"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--sequences", default=None, help="comma-separated subset (smoke tests)")
    ap.add_argument("--methods", default=None)
    ap.add_argument("--injections", default=None)
    ap.add_argument("--lengths", default=None)
    ap.add_argument("--window", type=int, default=12)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg_hash = config_sha256(cfg)

    with open(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    seqs = sorted(manifest["sequences"])
    if args.sequences:
        seqs = [s.strip() for s in args.sequences.split(",") if s.strip()]
    methods = cfg["methods"]
    if args.methods:
        keep = {m.strip() for m in args.methods.split(",")}
        methods = [m for m in methods if m["id"] in keep]
    injections = [InjectionSpec.from_dict(d) for d in cfg["injections"]]
    if args.injections:
        keep = {s.strip() for s in args.injections.split(",")}
        injections = [i for i in injections if i.id in keep]
    lengths = [int(x) for x in (args.lengths.split(",") if args.lengths else cfg["lengths"])]

    run_id = args.run_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{cfg['name']}_{cfg_hash[:8]}")
    root = os.path.join(args.workspace, "results", "runs")
    final = os.path.join(root, run_id)
    staging = os.path.join(root, f".staging_{run_id}")
    if os.path.exists(final):
        raise SystemExit(f"refusing to overwrite existing run dir {final}")
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    started = time.time()
    manifest_out = {
        "run_id": run_id, "kind": "tierA_matrix", "config_path": os.path.abspath(args.config),
        "config": cfg, "config_sha256": cfg_hash,
        "code_tree_sha256": code_tree_sha256([
            os.path.join(args.workspace, "project", "src"),
            os.path.join(args.workspace, "project", "scripts"),
            os.path.join(args.workspace, "project", "configs"),
        ]),
        "dataset_manifest_sha256": sha256_file(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json")),
        "environment": env_info(),
        "command": " ".join(sys.argv),
        "sequences": seqs, "methods": [m["id"] for m in methods],
        "injections": [i.id for i in injections], "lengths": lengths,
        "window": args.window,
        "overrides": {k: getattr(args, k) for k in ("sequences", "methods", "injections", "lengths")
                      if getattr(args, k)},
        "not_run": {
            "ffmpeg_filters": "NOT_RUN - no FFmpeg binary is used anywhere in this matrix; "
                              "no FFmpeg performance claim is made.",
            "all_in_one_cuda": "NOT_RUN - the All-In-One/Neural-Filtering adapter is not executed.",
            "deep_baselines": "NOT_RUN - B1-BlazeBVD / B2 / B3 / B4 / B5 require weights and a working "
                              "CUDA/PyTorch stack; no numbers are reported for them.",
        },
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(os.path.join(staging, "run_manifest.json"), manifest_out)

    pf = open(os.path.join(staging, "per_frame.csv"), "w", newline="", encoding="utf-8")
    ps = open(os.path.join(staging, "per_sequence.csv"), "w", newline="", encoding="utf-8")
    wf = csv.DictWriter(pf, fieldnames=PER_FRAME_FIELDS)
    ws = csv.DictWriter(ps, fieldnames=SUMMARY_FIELDS)
    wf.writeheader()
    ws.writeheader()

    total = len(seqs) * len(injections) * len(lengths) * len(methods)
    done = 0
    t_start = time.time()
    method_times: dict[str, float] = {}
    n_rows = 0
    try:
        for seq in seqs:
            ref = load_frames(os.path.join(args.workspace, "data", "frames", seq))
            l_ref = frame_luma_means(ref)
            for inj in injections:
                for length in lengths:
                    for method in methods:
                        t0 = time.perf_counter()
                        rows, summary = run_condition(ref, seq, inj, cfg["start"], length,
                                                      method, window=args.window,
                                                      l_ref=l_ref)
                        dt = time.perf_counter() - t0
                        method_times[method["id"]] = method_times.get(method["id"], 0.0) + dt
                        wf.writerows(rows)
                        ws.writerow({k: summary.get(k) for k in SUMMARY_FIELDS})
                        n_rows += len(rows)
                        done += 1
                        if done % 10 == 0 or done == total:
                            elapsed = time.time() - t_start
                            eta = elapsed / done * (total - done)
                            pf.flush()
                            ps.flush()
                            print(f"[{done}/{total}] {seq} {inj.id} len={length} {method['id']} "
                                  f"{dt:.2f}s elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m", flush=True)
    finally:
        pf.close()
        ps.close()

    finished = time.time()
    artifacts = {}
    for f in ("per_frame.csv", "per_sequence.csv"):
        p = os.path.join(staging, f)
        artifacts[f] = {"sha256": sha256_file(p), "bytes": os.path.getsize(p)}
    summary = {
        "run_id": run_id, "status": "SUCCESS",
        "n_conditions": total, "n_per_frame_rows": n_rows,
        "wall_seconds": finished - started,
        "method_seconds": method_times,
        "artifacts": artifacts,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(os.path.join(staging, "summary.json"), summary)
    with open(os.path.join(staging, "logs.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"command: {' '.join(sys.argv)}\n")
        fh.write(f"wall_seconds: {finished - started:.3f}\n")
    os.rename(staging, final)
    print(f"DONE {final}")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
