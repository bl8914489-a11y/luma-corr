"""Time each deterministic corrector on one 76-frame 512x512 clip (A, len12)."""
from __future__ import annotations

import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "results", "COST_2026-11-21.csv")
CFG = json.load(open(os.path.join(WS, "project", "configs", "matrix.json"), encoding="utf-8"))
ref = load_frames(os.path.join(WS, "data", "frames", "sailboat"))
inj = apply_injection(ref, InjectionSpec("A", "offset", 20.0, -1), 30, 12).injected
rows = []
for m in CFG["methods"]:
    cfg = dict(m); cfg["scope"] = "global" if m["id"] == "A4" else "local"
    ts = []
    for _ in range(2):
        t0 = time.perf_counter(); correct(cfg, inj, 30, 12); ts.append(time.perf_counter() - t0)
    rows.append({"method": m["id"], "kind": m["kind"], "seconds": round(min(ts), 4),
                 "ms_per_frame": round(1000 * min(ts) / 12, 2)})
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["method", "kind", "seconds", "ms_per_frame"]); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r)
