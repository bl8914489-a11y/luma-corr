"""Independent validation of a matrix run.

Re-executes a deterministic sample of conditions from scratch (same config,
same source frames) and compares the recorded aggregates, the per-frame errors
and the injected/corrected interval hashes.  A PASS means the table can be
recomputed from the code and the archived frames.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec  # noqa: E402
from luma_corr.pipeline import run_condition  # noqa: E402
from luma_corr.provenance import sha256_file, write_json_atomic  # noqa: E402

FIELDS = ["y_mae", "rgb_mae", "psnr", "ssim", "hist_dist",
          "outside_changed_pixel_fraction", "outside_rgb_mae",
          "boundary_jump_error_sum", "boundary_estimator_bias", "boundary_outside_jump"]


def close(a, b, tol=1e-9):
    if a is None or b is None:
        return False
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--sample", type=int, default=12)
    args = ap.parse_args()

    manifest = json.load(open(os.path.join(args.run_dir, "run_manifest.json"), encoding="utf-8"))
    cfg = manifest["config"]
    methods = {m["id"]: m for m in cfg["methods"]}
    injections = {d["id"]: InjectionSpec.from_dict(d) for d in cfg["injections"]}
    rows = list(csv.DictReader(open(os.path.join(args.run_dir, "per_sequence.csv"), encoding="utf-8")))
    step = max(1, len(rows) // args.sample)
    sample = rows[::step][:args.sample]

    frames_cache, luma_cache = {}, {}
    failures = []
    for i, r in enumerate(sample):
        seq = r["sequence"]
        if seq not in frames_cache:
            frames_cache[seq] = load_frames(os.path.join(args.workspace, "data", "frames", seq))
            luma_cache[seq] = frame_luma_means(frames_cache[seq])
        _, fresh = run_condition(frames_cache[seq], seq, injections[r["injection"]],
                                 int(r["start"]), int(r["length"]), methods[r["method"]],
                                 l_ref=luma_cache[seq])
        diffs = {}
        for f in FIELDS:
            if not close(r[f], fresh[f]):
                diffs[f] = [r[f], fresh[f]]
        for f in ("injected_interval_sha256", "corrected_interval_sha256"):
            if r[f] != fresh[f]:
                diffs[f] = [r[f], fresh[f]]
        if diffs:
            failures.append({"index": i, "sequence": seq, "injection": r["injection"],
                             "length": r["length"], "method": r["method"], "diffs": diffs})
        print(f"[{i+1}/{len(sample)}] {seq} {r['injection']} L{r['length']} {r['method']} "
              f"{'OK' if not diffs else 'FAIL'}", flush=True)

    report = {
        "run_dir": os.path.abspath(args.run_dir),
        "config_sha256": manifest["config_sha256"],
        "checked": len(sample), "passed": len(sample) - len(failures), "failed": len(failures),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "source_hashes": {f: sha256_file(os.path.join(args.run_dir, f))
                          for f in ("per_sequence.csv", "per_frame.csv")},
    }
    write_json_atomic(os.path.join(args.run_dir, "validation.json"), report)
    print(json.dumps({k: report[k] for k in ("status", "checked", "passed", "failed")}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
