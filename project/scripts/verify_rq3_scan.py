"""Freeze the RQ3 scan-statistic detector results."""
from __future__ import annotations

import csv
import hashlib
import json
import os

import numpy as np

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "rq3_scan_v1")
OUT = os.path.join(WS, "results", "FREEZE_RQ3_SCAN_2026-11-18.json")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


rows = list(csv.DictReader(open(os.path.join(RUN, "per_condition.csv"), encoding="utf-8")))
summary = json.load(open(os.path.join(RUN, "summary.json"), encoding="utf-8"))
checks = [
    ("117 conditions", len(rows), len(rows) == 117),
    ("test 81", len([r for r in rows if r["split"] == "test"]), len([r for r in rows if r["split"] == "test"]) == 81),
    ("validation 36", len([r for r in rows if r["split"] == "validation"]), len([r for r in rows if r["split"] == "validation"]) == 36),
    ("test len12 27", len([r for r in rows if r["split"] == "test" and int(r["length"]) == 12]),
     len([r for r in rows if r["split"] == "test" and int(r["length"]) == 12]) == 27),
]
status = "PASS" if all(c[2] for c in checks) else "FAIL"
out = {"freeze_id": "RQ3_SCAN_2026-11-18", "status": status,
       "checks": [{"name": a, "value": b, "pass": c} for a, b, c in checks],
       "summary": summary,
       "artifacts": {f: {"sha256": sha(os.path.join(RUN, f)), "bytes": os.path.getsize(os.path.join(RUN, f))}
                     for f in ("per_condition.csv", "summary.json")}}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(status, len(rows))
