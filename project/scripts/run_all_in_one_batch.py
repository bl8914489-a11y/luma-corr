"""Run All-In-One (CVPR 2023) on injected sequences: stage1 atlas + stage2 filter.

CPU/GPU environment: torch cu128 in third_party/pylibs, checkpoints in
third_party/All-In-One-Deflicker/pretrained_weights.  Each case takes ~8 min on
the RTX 5060 (8 GB); logs and outputs are kept per case.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
REPO = os.path.join(WS, "third_party", "All-In-One-Deflicker")
PYLIBS = os.path.join(WS, "third_party", "pylibs")
PY = sys.executable

CASES = [
    ("sailboat_B_len12", "sailboat", "B", 12),
    ("sailboat_A_len12", "sailboat", "A", 12),
    ("book_B_len12", "book", "B", 12),
    ("horse_A_len12", "horse", "A", 12),
    ("astronaut_B_len12", "astronaut", "B", 12),
    ("yoga_A_len12", "yoga", "A", 12),
    ("paint_A_len12", "paint", "A", 12),
    ("fish_B_len12", "fish", "B", 12),
    ("unicorn_B_len12", "unicorn", "B", 12),
    ("knight_A_len12", "knight", "A", 12),
    ("rabbit_B_len12", "rabbit", "B", 12),
    ("retriever_A_len12", "retriever", "A", 12),
    ("ship_A_len12", "ship", "A", 12),
    ("asteroids_B_len12", "asteroids", "B", 12),
]


def env():
    e = dict(os.environ)
    e["PYTHONPATH"] = REPO + ";" + PYLIBS
    e["MPLCONFIGDIR"] = os.path.join(WS, "third_party", "mplcache")
    e["MPLBACKEND"] = "Agg"
    try:
        import imageio_ffmpeg  # noqa: PLC0415
        e["PATH"] = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()) + ";" + e.get("PATH", "")
    except Exception:
        pass
    return e


def prepare(case, seq, inj, length):
    ref = load_frames(os.path.join(WS, "data", "frames", seq))
    spec = {"A": InjectionSpec("A", "offset", 20.0, -1),
            "B": InjectionSpec("B", "gamma", gamma=2.0),
            "B13": InjectionSpec("B13", "gamma", gamma=1.3)}[inj]
    frames = apply_injection(ref, spec, 30, length).injected
    dst = os.path.join(REPO, "data", "test", case)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for t in range(frames.shape[0]):
        Image.fromarray(frames[t]).save(os.path.join(dst, f"{t:05d}.png"))
    return len(frames)


def main() -> None:
    logs = os.path.join(WS, "third_party", "logs")
    os.makedirs(logs, exist_ok=True)
    results = []
    for case, seq, inj, length in CASES:
        final_dir = os.path.join(REPO, "results", case, "final", "output")
        if os.path.isdir(final_dir) and len([f for f in os.listdir(final_dir) if f.endswith(".png")]) >= 70:
            print("skip existing", case, flush=True)
            results.append({"case": case, "status": "existing"})
            continue
        n = prepare(case, seq, inj, length)
        res_dir = os.path.join(REPO, "results", case)
        if os.path.isdir(res_dir):
            shutil.rmtree(res_dir, ignore_errors=True)
        t0 = time.time()
        cmd1 = [PY, "src/stage1_neural_atlas.py", "--vid_name", case, "--root", "data/test",
                "--config", "config_flow_100_512.json", "--down", "4", "--gpu", "0"]
        with open(os.path.join(logs, f"{case}_stage1.log"), "w", encoding="utf-8") as fh:
            rc1 = subprocess.call(cmd1, cwd=REPO, env=env(), stdout=fh, stderr=subprocess.STDOUT)
        t1 = time.time()
        cmd2 = [PY, "src/neural_filter_and_refinement.py", "--video_name", case, "--fps", "10"]
        with open(os.path.join(logs, f"{case}_stage2.log"), "w", encoding="utf-8") as fh:
            rc2 = subprocess.call(cmd2, cwd=REPO, env=env(), stdout=fh, stderr=subprocess.STDOUT)
        t2 = time.time()
        n_out = len([f for f in os.listdir(final_dir) if f.endswith(".png")]) if os.path.isdir(final_dir) else 0
        results.append({"case": case, "frames_in": n, "frames_out": n_out,
                        "rc_stage1": rc1, "rc_stage2": rc2,
                        "stage1_s": round(t1 - t0, 1), "stage2_s": round(t2 - t1, 1),
                        "status": "ok" if n_out >= 70 else "failed"})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    with open(os.path.join(WS, "third_party", "batch_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    print("DONE")


if __name__ == "__main__":
    main()
