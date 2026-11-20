"""Multi-span scan on the three-interval scenarios (mixed and sameA)."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
CFG = json.load(open(os.path.join(WS, "project", "configs", "rq3_threshold_v1.json"), encoding="utf-8"))
OUT = os.path.join(WS, "results", "runs", "multi_scan_three_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
SPECS = {"A": InjectionSpec("A", "offset", 20.0, -1), "B": InjectionSpec("B", "gamma", gamma=2.0),
         "B13": InjectionSpec("B13", "gamma", gamma=1.3)}
SCEN = {"mixed": [(8, 4, "A"), (34, 8, "B"), (58, 12, "B13")],
        "sameA": [(8, 4, "A"), (34, 8, "A"), (58, 12, "A")]}
MAXL = 24
FIELDS = ["split", "scenario", "sequence", "max_spans", "threshold", "recall", "precision",
          "hit1", "hit2", "hit3", "n_spans", "pred_spans"]


def windows(frames):
    l = frame_luma_means(frames).astype(float)
    out = []
    for L in range(1, MAXL + 1):
        for s in range(0, len(l) - L + 1):
            e = s + L
            inside = l[s:e]
            outside = np.r_[l[:max(0, s - 2)], l[min(len(l), e + 2):]]
            if len(outside) < 8:
                outside = np.r_[l[:s], l[e:]]
            med = np.median(outside); mad = np.median(np.abs(outside - med))
            z = abs(inside.mean() - med) / max(1.4826 * mad, 1e-6) * np.sqrt(L)
            out.append((float(z), s, L))
    return out


def select(ws, thr, max_spans):
    picked = []; occupied = np.zeros(76, bool)
    for z, s, L in sorted(ws, key=lambda x: -x[0]):
        if z < thr:
            break
        if L < 2 or occupied[s:s + L].any():
            continue
        picked.append((s, L)); occupied[max(0, s - 1):min(76, s + L + 1)] = True
        if len(picked) >= max_spans:
            break
    return picked, occupied


def evaluate(picked, occupied, intervals):
    union = np.zeros(76, bool)
    for s, L, _ in intervals:
        union[s:s + L] = True
    tp = int((occupied & union).sum()); fp = int((occupied & ~union).sum()); fn = int((~occupied & union).sum())
    hits = [1.0 if occupied[s:s + L].sum() >= 0.5 * L else 0.0 for s, L, _ in intervals]
    return tp / max(tp + fn, 1), tp / max(tp + fp, 1), hits


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    cache = {}
    for seq in SEQS:
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for sc, intervals in SCEN.items():
            inj = ref
            for s, L, inj_id in intervals:
                inj = apply_injection(inj, SPECS[inj_id], s, L).injected
            cache[(seq, sc)] = windows(inj)
    grid = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20]
    best = None
    for ms in (2, 3):
        for thr in grid:
            vals = []
            for (seq, sc), ws in cache.items():
                if seq not in CFG["split"]["validation"]:
                    continue
                picked, occ = select(ws, thr, ms)
                r, p, _ = evaluate(picked, occ, SCEN[sc])
                vals.append((r, p))
            rec = np.mean([v[0] for v in vals]); pre = np.mean([v[1] for v in vals])
            f1 = 2 * rec * pre / max(rec + pre, 1e-9)
            if pre >= 0.50 and (best is None or f1 > best[4]):
                best = (ms, thr, rec, pre, f1, dict(zip([None], [None])))
    print("selected", best[:5], flush=True)
    ms, thr = best[0], best[1]
    rows = []
    for (seq, sc), ws in sorted(cache.items()):
        picked, occ = select(ws, thr, ms)
        r, p, hits = evaluate(picked, occ, SCEN[sc])
        rows.append({"split": "validation" if seq in CFG["split"]["validation"] else "test",
                     "scenario": sc, "sequence": seq, "max_spans": ms, "threshold": thr,
                     "recall": r, "precision": p, "hit1": hits[0], "hit2": hits[1], "hit3": hits[2],
                     "n_spans": len(picked), "pred_spans": ";".join(f"{s}-{s+L}" for s, L in picked)})
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(split, sc=None):
        rs = [r for r in rows if r["split"] == split and (sc is None or r["scenario"] == sc)]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in ("recall", "precision", "hit1", "hit2", "hit3", "n_spans")}
    summary = {"run_id": "multi_scan_three_v1", "max_spans": ms, "threshold": thr,
               "validation": agg("validation"), "test": agg("test"),
               "test_mixed": agg("test", "mixed"), "test_sameA": agg("test", "sameA"),
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
