"""End-to-end detection -> correction experiment.

For each synthetic condition, compare three correction inputs:
  * no-op (lower bound),
  * oracle interval (the injected [30,30+len)),
  * detected interval from the D1+D2 detector (blind).

The correction is the proposed A3 outside-linear k=3 offset.  Metrics are
always evaluated on the *true* interval, so a detector that fires on the wrong
frames is penalised twice: no restoration inside the truth, and outFrac outside.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.detection import detect  # noqa: E402
from luma_corr.detection_d1 import (d1_score, d2_spans, hist_stack, interval_metrics,  # noqa: E402
                                    robust_parts)
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import frame_metrics, sequence_metrics  # noqa: E402
from luma_corr.provenance import (code_tree_sha256, config_sha256, env_info, sha256_file,  # noqa: E402
                                  write_json_atomic)

FIELDS = ["sequence", "injection", "length", "chosen_start", "chosen_end", "det_hit", "det_iou",
          "ymae_noop", "ymae_oracle", "ymae_detected", "reduction_oracle", "reduction_detected",
          "outfrac_oracle", "outfrac_detected", "boundary_oracle", "boundary_detected",
          "correction_clip"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(r"F:\周四焜哥论文", "project", "configs", "detection_d1d2.json"))
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--run-id", default="rq3_e2e_v1")
    ap.add_argument("--detector", default="cusum", choices=["cusum", "d2"])
    ap.add_argument("--select", default="bestscore", choices=["first", "bestscore", "longest"])
    ap.add_argument("--h", type=float, default=6.0)
    ap.add_argument("--sequences", default=None)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    with open(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    seqs = sorted(manifest["sequences"])
    if args.sequences:
        seqs = [x.strip() for x in args.sequences.split(",") if x.strip()]
    start = int(cfg["start"])
    method = {"id": "A3", "kind": "offset_linear", "k": 3, "scope": "local"}
    root = os.path.join(args.workspace, "results", "runs")
    final = os.path.join(root, args.run_id)
    staging = os.path.join(root, f".staging_{args.run_id}")
    if os.path.exists(final):
        raise SystemExit(f"refusing to overwrite {final}")
    os.makedirs(staging, exist_ok=True)
    t0 = time.time()
    write_json_atomic(os.path.join(staging, "run_manifest.json"), {
        "run_id": args.run_id, "kind": "rq3_end_to_end", "config_sha256": config_sha256(cfg),
        "code_tree_sha256": code_tree_sha256([os.path.join(args.workspace, "project", "src")]),
        "environment": env_info(), "command": " ".join(sys.argv),
        "detector": {"kind": args.detector, "select": args.select, "h": args.h},
        "started_utc": datetime.now(timezone.utc).isoformat(),
    })

    rows = []
    for seq in seqs:
        ref = load_frames(os.path.join(args.workspace, "data", "frames", seq))
        l_ref = frame_luma_means(ref)
        for injd in cfg["injections"]:
            if injd["id"] == "CLEAN":
                continue
            spec = InjectionSpec.from_dict(injd)
            for length in cfg["lengths"]:
                inj = apply_injection(ref, spec, start, length).injected
                if args.detector == "cusum":
                    res = detect(inj, {"id": "cusum", "kind": "hist_kl_cusum", "bins": 64,
                                       "window": 41, "smooth": 3, "k": 0.5, "h": args.h, "min_len": 2})
                    spans = res["spans"]
                    score = res["score"]
                else:
                    H = hist_stack(inj, 64)
                    score = d1_score(H, 2.0, "js")
                    hi, med = robust_parts(score, 3.0)
                    lo = med + 0.5 * (hi - med)
                    spans = d2_spans(score, hi, lo, frame_luma_means(inj), min_len=2, max_gap=2,
                                     expand=True, refine=True)
                if not spans:
                    chosen = None
                elif args.select == "first":
                    chosen = spans[0]
                elif args.select == "longest":
                    chosen = max(spans, key=lambda ab: ab[1] - ab[0])
                else:
                    chosen = max(spans, key=lambda ab: float(np.mean(score[ab[0]:ab[1]])))
                im = interval_metrics(spans, start, length)

                noop = inj.copy()
                oracle = correct(method, inj, start, length)
                if chosen:
                    det_res = correct(method, inj, chosen[0], chosen[1] - chosen[0])
                    det_out = det_res.out
                else:
                    det_res = None
                    det_out = noop
                l_noop = frame_luma_means(noop)
                l_or = frame_luma_means(oracle.out)
                l_det = frame_luma_means(det_out)
                m_noop = sequence_metrics(noop, ref, start, length, l_noop, l_ref)
                m_or = sequence_metrics(oracle.out, ref, start, length, l_or, l_ref)
                m_det = sequence_metrics(det_out, ref, start, length, l_det, l_ref)
                y_noop = float(np.mean([frame_metrics(noop[t], ref[t])["y_mae"] for t in range(start, start + length)]))
                y_or = float(np.mean([frame_metrics(oracle.out[t], ref[t])["y_mae"] for t in range(start, start + length)]))
                y_det = float(np.mean([frame_metrics(det_out[t], ref[t])["y_mae"] for t in range(start, start + length)]))
                rows.append({
                    "sequence": seq, "injection": injd["id"], "length": length,
                    "chosen_start": chosen[0] if chosen else None, "chosen_end": chosen[1] if chosen else None,
                    "det_hit": im["interval_hit"], "det_iou": im["interval_iou"],
                    "ymae_noop": y_noop, "ymae_oracle": y_or, "ymae_detected": y_det,
                    "reduction_oracle": 1.0 - y_or / max(y_noop, 1e-9),
                    "reduction_detected": 1.0 - y_det / max(y_noop, 1e-9),
                    "outfrac_oracle": m_or["outside_changed_pixel_fraction"],
                    "outfrac_detected": m_det["outside_changed_pixel_fraction"],
                    "boundary_oracle": m_or["boundary_jump_error_sum"],
                    "boundary_detected": m_det["boundary_jump_error_sum"],
                    "correction_clip": oracle.info.get("clip_fraction", 0.0),
                })
                print(f"{seq} {injd['id']} L{length} span={chosen} "
                      f"YMAE noop/or/det={y_noop:.2f}/{y_or:.2f}/{y_det:.2f}", flush=True)

    with open(os.path.join(staging, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    a = np.array([[r["reduction_oracle"], r["reduction_detected"], r["outfrac_detected"],
                   r["det_hit"]] for r in rows], dtype=float)
    summary = {
        "run_id": args.run_id, "status": "SUCCESS", "n_conditions": len(rows),
        "wall_seconds": time.time() - t0,
        "mean_reduction_oracle": float(np.mean(a[:, 0])),
        "mean_reduction_detected": float(np.mean(a[:, 1])),
        "mean_outfrac_detected": float(np.mean(a[:, 2])),
        "detection_hit_rate": float(np.mean(a[:, 3])),
        "artifacts": {f: {"sha256": sha256_file(os.path.join(staging, f)),
                          "bytes": os.path.getsize(os.path.join(staging, f))}
                      for f in ("per_condition.csv",)},
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(os.path.join(staging, "summary.json"), summary)
    os.rename(staging, final)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
