"""Run the full B2 matrix: 13 sequences x 3 injections x lengths 1/4/12 (117 cases)."""
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
    with open(os.path.join(WS, "third_party", "batch_summary_full.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("DONE")


if __name__ == "__main__":
    main()
