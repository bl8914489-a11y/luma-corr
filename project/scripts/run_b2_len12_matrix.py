"""Run All-In-One on the balanced len-12 matrix: 13 sequences x 3 injections."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_all_in_one_batch import REPO, PY, env, prepare  # noqa: E402

WS = r"F:\周四焜哥论文"
CASES = [
    ("asteroids_A_len12", "asteroids", "A", 12),
    ("asteroids_B_len12", "asteroids", "B", 12),
    ("asteroids_B13_len12", "asteroids", "B13", 12),
    ("astronaut_A_len12", "astronaut", "A", 12),
    ("astronaut_B_len12", "astronaut", "B", 12),
    ("astronaut_B13_len12", "astronaut", "B13", 12),
    ("book_A_len12", "book", "A", 12),
    ("book_B_len12", "book", "B", 12),
    ("book_B13_len12", "book", "B13", 12),
    ("fish_A_len12", "fish", "A", 12),
    ("fish_B_len12", "fish", "B", 12),
    ("fish_B13_len12", "fish", "B13", 12),
    ("horse_A_len12", "horse", "A", 12),
    ("horse_B_len12", "horse", "B", 12),
    ("horse_B13_len12", "horse", "B13", 12),
    ("knight_A_len12", "knight", "A", 12),
    ("knight_B_len12", "knight", "B", 12),
    ("knight_B13_len12", "knight", "B13", 12),
    ("paint_A_len12", "paint", "A", 12),
    ("paint_B_len12", "paint", "B", 12),
    ("paint_B13_len12", "paint", "B13", 12),
    ("rabbit_A_len12", "rabbit", "A", 12),
    ("rabbit_B_len12", "rabbit", "B", 12),
    ("rabbit_B13_len12", "rabbit", "B13", 12),
    ("retriever_A_len12", "retriever", "A", 12),
    ("retriever_B_len12", "retriever", "B", 12),
    ("retriever_B13_len12", "retriever", "B13", 12),
    ("sailboat_A_len12", "sailboat", "A", 12),
    ("sailboat_B_len12", "sailboat", "B", 12),
    ("sailboat_B13_len12", "sailboat", "B13", 12),
    ("ship_A_len12", "ship", "A", 12),
    ("ship_B_len12", "ship", "B", 12),
    ("ship_B13_len12", "ship", "B13", 12),
    ("unicorn_A_len12", "unicorn", "A", 12),
    ("unicorn_B_len12", "unicorn", "B", 12),
    ("unicorn_B13_len12", "unicorn", "B13", 12),
    ("yoga_A_len12", "yoga", "A", 12),
    ("yoga_B_len12", "yoga", "B", 12),
    ("yoga_B13_len12", "yoga", "B13", 12),
]


def main():
    logs = os.path.join(WS, "third_party", "logs")
    os.makedirs(logs, exist_ok=True)
    out = []
    for case, seq, inj, length in CASES:
        final_dir = os.path.join(REPO, "results", case, "final", "output")
        if os.path.isdir(final_dir) and len([f for f in os.listdir(final_dir) if f.endswith(".png")]) >= 70:
            print("skip", case, flush=True)
            out.append({"case": case, "status": "existing"})
            continue
        n = prepare(case, seq, inj, length)
        res = os.path.join(REPO, "results", case)
        if os.path.isdir(res):
            shutil.rmtree(res, ignore_errors=True)
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
        rec = {"case": case, "frames_in": n, "frames_out": n_out, "rc_stage1": rc1, "rc_stage2": rc2,
               "stage1_s": round(t1 - t0, 1), "stage2_s": round(t2 - t1, 1),
               "status": "ok" if n_out >= 70 else "failed"}
        out.append(rec); print(json.dumps(rec, ensure_ascii=False), flush=True)
    with open(os.path.join(WS, "third_party", "batch_summary_len12.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("DONE")


if __name__ == "__main__":
    main()
