"""Run All-In-One on the two three-interval scenarios (26 cases)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_all_in_one_batch import REPO, PY, env  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from PIL import Image  # noqa: E402

WS = r"F:\周四焜哥论文"
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
SPECS = {"A": InjectionSpec("A", "offset", 20.0, -1), "B": InjectionSpec("B", "gamma", gamma=2.0),
         "B13": InjectionSpec("B13", "gamma", gamma=1.3)}
SCEN = {"mixed": [(8, 4, "A"), (34, 8, "B"), (58, 12, "B13")],
        "sameA": [(8, 4, "A"), (34, 8, "A"), (58, 12, "A")]}
CASES = [(f"m3_{s}_{sc}", s, sc) for s in SEQS for sc in SCEN]


def prepare(case, seq, sc):
    ref = load_frames(os.path.join(WS, "data", "frames", seq))
    frames = ref
    for s, L, inj in SCEN[sc]:
        frames = apply_injection(frames, SPECS[inj], s, L).injected
    dst = os.path.join(REPO, "data", "test", case)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for t in range(frames.shape[0]):
        Image.fromarray(frames[t]).save(os.path.join(dst, f"{t:05d}.png"))
    return len(frames)


def main():
    logs = os.path.join(WS, "third_party", "logs"); os.makedirs(logs, exist_ok=True)
    out = []
    for case, seq, sc in CASES:
        final = os.path.join(REPO, "results", case, "final", "output")
        if os.path.isdir(final) and len([f for f in os.listdir(final) if f.endswith(".png")]) >= 70:
            print("skip", case, flush=True); out.append({"case": case, "status": "existing"}); continue
        n = prepare(case, seq, sc)
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
        n_out = len([f for f in os.listdir(final) if f.endswith(".png")]) if os.path.isdir(final) else 0
        rec = {"case": case, "frames_in": n, "frames_out": n_out, "rc_stage1": rc1, "rc_stage2": rc2,
               "stage1_s": round(t1 - t0, 1), "stage2_s": round(t2 - t1, 1),
               "status": "ok" if n_out >= 70 else "failed"}
        out.append(rec); print(json.dumps(rec, ensure_ascii=False), flush=True)
    json.dump(out, open(os.path.join(WS, "third_party", "batch_summary_three_b2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("DONE")


if __name__ == "__main__":
    main()
