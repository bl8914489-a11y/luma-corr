"""Wait for the 117-case B2 matrix, then evaluate it and write a readiness marker."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np

WS = r"F:\周四焜哥论文"
REPO = os.path.join(WS, "third_party", "All-In-One-Deflicker")
PY = sys.executable
N = 117


def count_done():
    root = os.path.join(REPO, "results")
    if not os.path.isdir(root):
        return 0
    n = 0
    for d in os.listdir(root):
        out = os.path.join(root, d, "final", "output")
        if os.path.isdir(out) and len([f for f in os.listdir(out) if f.endswith(".png")]) >= 70:
            n += 1
    return n


def main():
    log = os.path.join(WS, "results", "B2_FULL_WATCH.log")
    while True:
        n = count_done()
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} done={n}/{N}\n")
        if n >= N:
            time.sleep(120)
            if count_done() >= N:
                break
        time.sleep(300)
    env = dict(os.environ); env["B2_RUN_ID"] = "b2_full_v1"
    subprocess.call([PY, os.path.join(WS, "project", "scripts", "eval_all_in_one.py")],
                    cwd=WS, env=env)
    subprocess.call([PY, os.path.join(WS, "project", "scripts", "verify_b2_full.py")],
                    cwd=WS, env=env)
    run = os.path.join(WS, "results", "runs", "b2_full_v1")
    rows = list(csv.DictReader(open(os.path.join(run, "per_case.csv"), encoding="utf-8")))
    lines = ["# B2 full matrix (117 cases)", "", "13 sequences x 3 injections x lengths 1/4/12, len12 table is the paper's main setting.", ""]
    for L in (1, 4, 12):
        lines.append(f"## len{L}")
        lines.append("| injection | no-op | A3 | B2 | B2 outFrac | B2 outside RGB |")
        lines.append("|---|---|---|---|---|---|")
        for inj in ("A", "B", "B13"):
            def m(method, key):
                v = [float(r[key]) for r in rows if int(r["length"]) == L and r["injection"] == inj and r["method"] == method]
                return float(np.mean(v))
            lines.append(f"| {inj} | {m('noop','y_mae'):.2f} | {m('A3','y_mae'):.2f} | "
                         f"{m('B2_all_in_one','y_mae'):.2f} | {100*m('B2_all_in_one','outfrac'):.2f}% | "
                         f"{m('B2_all_in_one','outside_rgb_mae'):.2f} |")
        lines.append("")
    open(os.path.join(WS, "results", "B2_FULL_2026-11-18.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    with open(os.path.join(WS, "results", "B2_FULL_READY.json"), "w", encoding="utf-8") as fh:
        json.dump({"status": "READY", "cases": len({r["case"] for r in rows}),
                   "finished_utc": datetime.now(timezone.utc).isoformat()}, fh, indent=1)
    print("READY")


if __name__ == "__main__":
    main()
