"""Verify and freeze the 117-case B2 matrix after evaluation."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "b2_full_v1")
OUT = os.path.join(WS, "results", "FREEZE_B2_FULL_2026-11-18.json")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    rows = list(csv.DictReader(open(os.path.join(RUN, "per_case.csv"), encoding="utf-8")))
    cases = {r["case"] for r in rows}
    summary = json.load(open(os.path.join(RUN, "summary.json"), encoding="utf-8"))
    checks = []
    checks.append({"name": "117 cases", "value": len(cases), "pass": len(cases) == 117})
    checks.append({"name": "351 method rows", "value": len(rows), "pass": len(rows) == 351})
    for L in (1, 4, 12):
        n = len({r["case"] for r in rows if int(r["length"]) == L})
        checks.append({"name": f"len{L} 39 cases", "value": n, "pass": n == 39})
    means = summary.get("interval_mean", {})
    checks.append({"name": "B2 mean present", "value": "B2_all_in_one" in means,
                   "pass": "B2_all_in_one" in means})
    status = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    out = {"freeze_id": "B2_FULL_2026-11-18", "status": status, "checks": checks,
           "n_cases": len(cases), "n_rows": len(rows),
           "interval_mean": means,
           "artifacts": {f: {"sha256": sha(os.path.join(RUN, f)),
                             "bytes": os.path.getsize(os.path.join(RUN, f))}
                         for f in ("per_case.csv", "summary.json")},
           "created_utc": datetime.now(timezone.utc).isoformat()}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(status, len(cases), len(rows))


if __name__ == "__main__":
    main()
