"""Cluster-bootstrap uncertainty for RQ3, end-to-end and B2 comparisons."""
from __future__ import annotations

import csv
import itertools
import json
import os
from datetime import datetime, timezone

import numpy as np

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "results", "UNCERTAINTY_2026-11-18.json")
MD = os.path.join(WS, "results", "UNCERTAINTY_2026-11-18.md")
RNG = np.random.default_rng(20261118)
NBOOT = 4000


def read(p):
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def boot_cluster(rows, value_col, cluster_col="sequence", stat=np.mean):
    clusters = sorted({r[cluster_col] for r in rows})
    vals = []
    for _ in range(NBOOT):
        pick = RNG.choice(clusters, size=len(clusters), replace=True)
        sample = []
        for c in pick:
            sample.extend(float(r[value_col]) for r in rows if r[cluster_col] == c)
        vals.append(float(stat(sample)))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def exact_signflip(d):
    d = np.asarray(d, float)
    obs = abs(d.mean())
    n = len(d)
    if n > 20:
        m = 20000
        cnt = 0
        for _ in range(m):
            signs = RNG.choice([-1, 1], size=n)
            if abs((d * signs).mean()) >= obs - 1e-12:
                cnt += 1
        return (cnt + 1) / (m + 1)
    cnt = 0
    for signs in itertools.product([-1, 1], repeat=n):
        if abs((d * np.array(signs)).mean()) >= obs - 1e-12:
            cnt += 1
    return cnt / (2 ** n)


def main():
    rq3 = read(os.path.join(WS, "results", "runs", "rq3_test_errors_v1", "per_condition.csv"))
    e2e = read(os.path.join(WS, "results", "runs", "rq3_e2e_test_v1", "per_condition.csv"))
    b2 = read(os.path.join(WS, "results", "runs", os.environ.get("B2_RUN_ID", "b2_len12_v1"), "per_case.csv"))

    out = {"created_utc": datetime.now(timezone.utc).isoformat(), "n_boot": NBOOT}
    out["rq3_test_recall"] = {"mean": float(np.mean([float(r["recall"]) for r in rq3])),
                              "ci95": boot_cluster(rq3, "recall")}
    out["rq3_test_precision"] = {"mean": float(np.mean([float(r["precision"]) for r in rq3])),
                                 "ci95": boot_cluster(rq3, "precision")}
    out["e2e_reduction_detected"] = {"mean": float(np.mean([float(r["reduction_detected"]) for r in e2e])),
                                     "ci95": boot_cluster(e2e, "reduction_detected")}
    out["e2e_outfrac_detected"] = {"mean": float(np.mean([float(r["outfrac_detected"]) for r in e2e])),
                                   "ci95": boot_cluster(e2e, "outfrac_detected")}

    by = {}
    for r in b2:
        by.setdefault(r["case"], {})[r["method"]] = r
    cases = sorted(by)
    diffs = [float(by[c]["B2_all_in_one"]["y_mae"]) - float(by[c]["A3"]["y_mae"]) for c in cases]
    out["b2_minus_a3_y_mae"] = {"mean": float(np.mean(diffs)),
                                "ci95": [float(np.percentile([np.mean(RNG.choice(diffs, len(diffs), replace=True))
                                                              for _ in range(NBOOT)], 2.5)),
                                         float(np.percentile([np.mean(RNG.choice(diffs, len(diffs), replace=True))
                                                              for _ in range(NBOOT)], 97.5))],
                                "signflip_p": exact_signflip(diffs), "n_cases": len(cases)}
    out["b2_minus_a3_outside_rgb"] = {
        "mean": float(np.mean([float(by[c]["B2_all_in_one"]["outside_rgb_mae"])
                               - float(by[c]["A3"]["outside_rgb_mae"]) for c in cases]))}

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    lines = ["# Cluster-bootstrap uncertainty (2026-11-18)", "",
             f"{NBOOT} resamples over video clusters; 95% percentile intervals.", ""]
    for k in ("rq3_test_recall", "rq3_test_precision", "e2e_reduction_detected", "e2e_outfrac_detected"):
        v = out[k]
        lines.append(f"- {k}: mean {v['mean']:.4f}, 95% CI [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]")
    d = out["b2_minus_a3_y_mae"]
    lines.append(f"- B2 - A3 Y-MAE: mean {d['mean']:.3f}, 95% CI [{d['ci95'][0]:.3f}, {d['ci95'][1]:.3f}], "
                 f"sign-flip Monte Carlo p={d['signflip_p']:.4g}, n={d['n_cases']}")
    with open(MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
