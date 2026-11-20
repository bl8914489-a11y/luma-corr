"""Run the RQ3 detection comparison.

Uses the same injected intervals as the correction matrix plus clean-sequence
false-positive probes.  No ground truth beyond the injected interval is used by
the detectors; thresholds are derived from the score distribution.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import detect, evaluate_detection  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.provenance import (code_tree_sha256, config_sha256, env_info, sha256_file,  # noqa: E402
                                  write_json_atomic)

FIELDS = ["sequence", "injection", "length", "detector", "tp", "fp", "fn", "recall", "precision",
          "iou", "f1", "fp_rate", "n_spans", "detected_span_start", "detected_span_end",
          "boundary_abs_error_mean", "start_delay", "threshold_hi", "threshold_lo"]
PF_FIELDS = ["sequence", "injection", "length", "detector", "t", "score", "mask", "label"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--sequences", default=None)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg_hash = config_sha256(cfg)
    with open(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    seqs = sorted(manifest["sequences"]) if not args.sequences else [s.strip() for s in args.sequences.split(",")]
    run_id = args.run_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_rq3_{cfg_hash[:8]}")
    root = os.path.join(args.workspace, "results", "runs")
    final = os.path.join(root, run_id)
    staging = os.path.join(root, f".staging_{run_id}")
    if os.path.exists(final):
        raise SystemExit(f"refusing to overwrite {final}")
    os.makedirs(staging, exist_ok=True)

    started = time.time()
    write_json_atomic(os.path.join(staging, "run_manifest.json"), {
        "run_id": run_id, "kind": "rq3_detection", "config": cfg, "config_sha256": cfg_hash,
        "code_tree_sha256": code_tree_sha256([os.path.join(args.workspace, "project", "src"),
                                              os.path.join(args.workspace, "project", "configs")]),
        "dataset_manifest_sha256": sha256_file(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json")),
        "environment": env_info(), "command": " ".join(sys.argv), "sequences": seqs,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "not_run": {"ffmpeg_filters": "NOT_RUN", "all_in_one_cuda": "NOT_RUN"},
    })

    sf = open(os.path.join(staging, "per_condition.csv"), "w", newline="", encoding="utf-8")
    pf = open(os.path.join(staging, "per_frame.csv"), "w", newline="", encoding="utf-8")
    ws, wp = csv.DictWriter(sf, fieldnames=FIELDS), csv.DictWriter(pf, fieldnames=PF_FIELDS)
    ws.writeheader()
    wp.writeheader()

    n = 0
    for seq in seqs:
        ref = load_frames(os.path.join(args.workspace, "data", "frames", seq))
        for injd in cfg["injections"]:
            inj = InjectionSpec.from_dict(injd) if injd["kind"] != "none" else None
            lengths = [0] if inj is None else cfg["lengths"]
            for length in lengths:
                frames = ref if inj is None else apply_injection(ref, inj, cfg["start"], length).injected
                for det in cfg["detectors"]:
                    res = detect(frames, det)
                    ev = evaluate_detection(res, cfg["start"], length)
                    span = ev["detected_span"] or (None, None)
                    ws.writerow({
                        "sequence": seq, "injection": injd["id"], "length": length,
                        "detector": det["id"], "tp": ev["tp"], "fp": ev["fp"], "fn": ev["fn"],
                        "recall": ev["recall"], "precision": ev["precision"], "iou": ev["iou"],
                        "f1": ev["f1"], "fp_rate": ev["fp"] / max(len(ref), 1),
                        "n_spans": len(ev["detected_spans"]),
                        "detected_span_start": span[0], "detected_span_end": span[1],
                        "boundary_abs_error_mean": ev["boundary_abs_error_mean"],
                        "start_delay": ev["start_delay"],
                        "threshold_hi": ev["threshold_hi"], "threshold_lo": ev["threshold_lo"],
                    })
                    label = [0] * len(ref)
                    if length:
                        for t in range(cfg["start"], cfg["start"] + length):
                            label[t] = 1
                    for t in range(len(ref)):
                        wp.writerow({"sequence": seq, "injection": injd["id"], "length": length,
                                     "detector": det["id"], "t": t, "score": float(res["score"][t]),
                                     "mask": int(res["mask"][t]), "label": label[t]})
                    n += 1
                    print(f"{seq} {injd['id']} len={length} {det['id']} R={ev['recall']:.2f} "
                          f"P={ev['precision']:.2f} IoU={ev['iou']:.2f}", flush=True)
    sf.close()
    pf.close()

    artifacts = {f: {"sha256": sha256_file(os.path.join(staging, f)),
                     "bytes": os.path.getsize(os.path.join(staging, f))}
                 for f in ("per_condition.csv", "per_frame.csv")}
    summary = {"run_id": run_id, "status": "SUCCESS", "n_conditions": n,
               "wall_seconds": time.time() - started, "artifacts": artifacts,
               "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(staging, "summary.json"), summary)
    os.rename(staging, final)
    print("DONE", final)


if __name__ == "__main__":
    main()
