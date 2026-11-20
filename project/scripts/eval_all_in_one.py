"""Evaluate All-In-One outputs against the clean reference.

For each injected case we compare:
  * no-op (injected sequence),
  * A3 local linear k=3 (known interval),
  * B2 All-In-One (blind, whole sequence).

Metrics are always reported on the *true* interval [30,30+len); outFrac counts
changes outside that interval, so a blind global method is penalised for
touching frames the task says should be preserved.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames, sha256_array_uint8  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import frame_metrics, sequence_metrics  # noqa: E402
from luma_corr.provenance import env_info, sha256_file, write_json_atomic  # noqa: E402

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
REPO = os.path.join(WS, "third_party", "All-In-One-Deflicker")
CASES = [
    ("asteroids_A_len1", "asteroids", "A", 1),
    ("asteroids_A_len4", "asteroids", "A", 4),
    ("asteroids_A_len12", "asteroids", "A", 12),
    ("asteroids_B_len1", "asteroids", "B", 1),
    ("asteroids_B_len4", "asteroids", "B", 4),
    ("asteroids_B_len12", "asteroids", "B", 12),
    ("asteroids_B13_len1", "asteroids", "B13", 1),
    ("asteroids_B13_len4", "asteroids", "B13", 4),
    ("asteroids_B13_len12", "asteroids", "B13", 12),
    ("astronaut_A_len1", "astronaut", "A", 1),
    ("astronaut_A_len4", "astronaut", "A", 4),
    ("astronaut_A_len12", "astronaut", "A", 12),
    ("astronaut_B_len1", "astronaut", "B", 1),
    ("astronaut_B_len4", "astronaut", "B", 4),
    ("astronaut_B_len12", "astronaut", "B", 12),
    ("astronaut_B13_len1", "astronaut", "B13", 1),
    ("astronaut_B13_len4", "astronaut", "B13", 4),
    ("astronaut_B13_len12", "astronaut", "B13", 12),
    ("book_A_len1", "book", "A", 1),
    ("book_A_len4", "book", "A", 4),
    ("book_A_len12", "book", "A", 12),
    ("book_B_len1", "book", "B", 1),
    ("book_B_len4", "book", "B", 4),
    ("book_B_len12", "book", "B", 12),
    ("book_B13_len1", "book", "B13", 1),
    ("book_B13_len4", "book", "B13", 4),
    ("book_B13_len12", "book", "B13", 12),
    ("fish_A_len1", "fish", "A", 1),
    ("fish_A_len4", "fish", "A", 4),
    ("fish_A_len12", "fish", "A", 12),
    ("fish_B_len1", "fish", "B", 1),
    ("fish_B_len4", "fish", "B", 4),
    ("fish_B_len12", "fish", "B", 12),
    ("fish_B13_len1", "fish", "B13", 1),
    ("fish_B13_len4", "fish", "B13", 4),
    ("fish_B13_len12", "fish", "B13", 12),
    ("horse_A_len1", "horse", "A", 1),
    ("horse_A_len4", "horse", "A", 4),
    ("horse_A_len12", "horse", "A", 12),
    ("horse_B_len1", "horse", "B", 1),
    ("horse_B_len4", "horse", "B", 4),
    ("horse_B_len12", "horse", "B", 12),
    ("horse_B13_len1", "horse", "B13", 1),
    ("horse_B13_len4", "horse", "B13", 4),
    ("horse_B13_len12", "horse", "B13", 12),
    ("knight_A_len1", "knight", "A", 1),
    ("knight_A_len4", "knight", "A", 4),
    ("knight_A_len12", "knight", "A", 12),
    ("knight_B_len1", "knight", "B", 1),
    ("knight_B_len4", "knight", "B", 4),
    ("knight_B_len12", "knight", "B", 12),
    ("knight_B13_len1", "knight", "B13", 1),
    ("knight_B13_len4", "knight", "B13", 4),
    ("knight_B13_len12", "knight", "B13", 12),
    ("paint_A_len1", "paint", "A", 1),
    ("paint_A_len4", "paint", "A", 4),
    ("paint_A_len12", "paint", "A", 12),
    ("paint_B_len1", "paint", "B", 1),
    ("paint_B_len4", "paint", "B", 4),
    ("paint_B_len12", "paint", "B", 12),
    ("paint_B13_len1", "paint", "B13", 1),
    ("paint_B13_len4", "paint", "B13", 4),
    ("paint_B13_len12", "paint", "B13", 12),
    ("rabbit_A_len1", "rabbit", "A", 1),
    ("rabbit_A_len4", "rabbit", "A", 4),
    ("rabbit_A_len12", "rabbit", "A", 12),
    ("rabbit_B_len1", "rabbit", "B", 1),
    ("rabbit_B_len4", "rabbit", "B", 4),
    ("rabbit_B_len12", "rabbit", "B", 12),
    ("rabbit_B13_len1", "rabbit", "B13", 1),
    ("rabbit_B13_len4", "rabbit", "B13", 4),
    ("rabbit_B13_len12", "rabbit", "B13", 12),
    ("retriever_A_len1", "retriever", "A", 1),
    ("retriever_A_len4", "retriever", "A", 4),
    ("retriever_A_len12", "retriever", "A", 12),
    ("retriever_B_len1", "retriever", "B", 1),
    ("retriever_B_len4", "retriever", "B", 4),
    ("retriever_B_len12", "retriever", "B", 12),
    ("retriever_B13_len1", "retriever", "B13", 1),
    ("retriever_B13_len4", "retriever", "B13", 4),
    ("retriever_B13_len12", "retriever", "B13", 12),
    ("sailboat_A_len1", "sailboat", "A", 1),
    ("sailboat_A_len4", "sailboat", "A", 4),
    ("sailboat_A_len12", "sailboat", "A", 12),
    ("sailboat_B_len1", "sailboat", "B", 1),
    ("sailboat_B_len4", "sailboat", "B", 4),
    ("sailboat_B_len12", "sailboat", "B", 12),
    ("sailboat_B13_len1", "sailboat", "B13", 1),
    ("sailboat_B13_len4", "sailboat", "B13", 4),
    ("sailboat_B13_len12", "sailboat", "B13", 12),
    ("ship_A_len1", "ship", "A", 1),
    ("ship_A_len4", "ship", "A", 4),
    ("ship_A_len12", "ship", "A", 12),
    ("ship_B_len1", "ship", "B", 1),
    ("ship_B_len4", "ship", "B", 4),
    ("ship_B_len12", "ship", "B", 12),
    ("ship_B13_len1", "ship", "B13", 1),
    ("ship_B13_len4", "ship", "B13", 4),
    ("ship_B13_len12", "ship", "B13", 12),
    ("unicorn_A_len1", "unicorn", "A", 1),
    ("unicorn_A_len4", "unicorn", "A", 4),
    ("unicorn_A_len12", "unicorn", "A", 12),
    ("unicorn_B_len1", "unicorn", "B", 1),
    ("unicorn_B_len4", "unicorn", "B", 4),
    ("unicorn_B_len12", "unicorn", "B", 12),
    ("unicorn_B13_len1", "unicorn", "B13", 1),
    ("unicorn_B13_len4", "unicorn", "B13", 4),
    ("unicorn_B13_len12", "unicorn", "B13", 12),
    ("yoga_A_len1", "yoga", "A", 1),
    ("yoga_A_len4", "yoga", "A", 4),
    ("yoga_A_len12", "yoga", "A", 12),
    ("yoga_B_len1", "yoga", "B", 1),
    ("yoga_B_len4", "yoga", "B", 4),
    ("yoga_B_len12", "yoga", "B", 12),
    ("yoga_B13_len1", "yoga", "B13", 1),
    ("yoga_B13_len4", "yoga", "B13", 4),
    ("yoga_B13_len12", "yoga", "B13", 12),
]
FIELDS = ["case", "sequence", "injection", "length", "method", "frames",
          "y_mae", "rgb_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary", "flicker_var"]


def load_output(case: str, n: int) -> np.ndarray:
    d = os.path.join(REPO, "results", case, "final", "output")
    files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    if len(files) < n:
        raise FileNotFoundError(f"{d}: {len(files)} frames, expected {n}")
    frames = []
    for f in files[:n]:
        im = Image.open(os.path.join(d, f)).convert("RGB")
        frames.append(np.asarray(im, dtype=np.uint8))
    return np.stack(frames)


def main() -> None:
    run_id = os.environ.get("B2_RUN_ID", "b2_all_in_one_v1")
    root = os.path.join(WS, "results", "runs")
    final = os.path.join(root, run_id)
    staging = os.path.join(root, f".staging_{run_id}")
    if os.path.exists(final):
        raise SystemExit(f"exists {final}")
    os.makedirs(staging, exist_ok=True)
    t0 = time.time()
    meta = {
        "run_id": run_id, "kind": "deep_baseline_eval",
        "model": "All-In-One Deflicker (CVPR 2023), official code + weights",
        "repo": "https://github.com/ChenyangLEI/All-In-One-Deflicker",
        "weight_sha256": {f: sha256_file(os.path.join(REPO, "pretrained_weights", f))
                          for f in ("neural_filter.pth", "local_refinement_net.pth", "raft-things.pth")},
        "config": {"resx": 512, "resy": 512, "iters_num": 10000, "down": 4, "fps": 10},
        "environment": env_info(), "started_utc": datetime.now(timezone.utc).isoformat(),
        "not_run": {"blazebvd": "official code not publicly released as of 2026-11-17; no number claimed"},
    }
    write_json_atomic(os.path.join(staging, "run_manifest.json"), meta)

    rows = []
    for case, seq, inj_id, length in CASES:
        final_dir = os.path.join(REPO, "results", case, "final", "output")
        if not os.path.isdir(final_dir):
            print("missing", case)
            continue
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        spec = {"A": InjectionSpec("A", "offset", 20.0, -1),
                "B": InjectionSpec("B", "gamma", gamma=2.0),
                "B13": InjectionSpec("B13", "gamma", gamma=1.3)}[inj_id]
        inj = apply_injection(ref, spec, 30, length).injected
        out = load_output(case, ref.shape[0])
        if out.shape != ref.shape:
            raise ValueError(f"{case}: output {out.shape} != ref {ref.shape}")
        l_ref = frame_luma_means(ref)
        a3 = correct({"id": "A3", "kind": "offset_linear", "k": 3, "scope": "local"},
                     inj, 30, length)
        methods = {"noop": inj, "A3": a3.out, "B2_all_in_one": out}
        for name, arr in methods.items():
            l_out = frame_luma_means(arr)
            agg = sequence_metrics(arr, ref, 30, length, l_out, l_ref)
            fm = [frame_metrics(arr[t], ref[t], with_ssim=(30 <= t < 30 + length))
                  for t in range(30, 30 + length)]
            rows.append({
                "case": case, "sequence": seq, "injection": inj_id, "length": length,
                "method": name, "frames": int(ref.shape[0]),
                "y_mae": float(np.mean([x["y_mae"] for x in fm])),
                "rgb_mae": float(np.mean([x["rgb_mae"] for x in fm])),
                "psnr": float(np.mean([x["psnr"] for x in fm])),
                "ssim": float(np.mean([x["ssim"] for x in fm])),
                "outfrac": agg["outside_changed_pixel_fraction"],
                "outside_rgb_mae": agg["outside_rgb_mae"],
                "boundary": agg["boundary_jump_error_sum"],
                "flicker_var": agg["flicker_first_diff_var"],
            })
        print(case, "done", flush=True)

    with open(os.path.join(staging, "per_case.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    summary = {"run_id": run_id, "status": "SUCCESS", "wall_seconds": time.time() - t0,
               "n_rows": len(rows),
               "interval_mean": {m: {k: float(np.mean([r[k] for r in rows if r["method"] == m]))
                                     for k in ("y_mae", "rgb_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary")}
                                 for m in ("noop", "A3", "B2_all_in_one")},
               "artifacts": {f: {"sha256": sha256_file(os.path.join(staging, f)),
                                 "bytes": os.path.getsize(os.path.join(staging, f))}
                             for f in ("per_case.csv",)},
               "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(staging, "summary.json"), summary)
    os.rename(staging, final)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
