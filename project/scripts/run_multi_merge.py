"""Merge/refine multi-interval detector: seed -> expand -> merge -> non-overlap."""
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
OUT = os.path.join(WS, "results", "runs", "multi_merge_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
SPECS = {"A": InjectionSpec("A", "offset", 20.0, -1), "B": InjectionSpec("B", "gamma", gamma=2.0),
         "B13": InjectionSpec("B13", "gamma", gamma=1.3)}
TWO = {"A": [(10, 4), (50, 4)], "B": [(10, 4), (50, 4)], "A12": [(10, 12), (50, 12)], "B12": [(10, 12), (50, 12)]}
THREE = {"mixed": [(8, 4, "A"), (34, 8, "B"), (58, 12, "B13")],
         "sameA": [(8, 4, "A"), (34, 8, "A"), (58, 12, "A")]}
MAXL = 24
FIELDS = ["dataset", "scenario", "split", "sequence", "injection", "length", "hi", "lo",
          "max_spans", "recall", "precision", "hit1", "hit2", "hit3", "n_spans", "pred_spans"]


def scan(frames):
    l = frame_luma_means(frames).astype(float)
    med = np.median(l); mad = np.median(np.abs(l - med))
    zf = np.abs(l - med) / max(1.4826 * mad, 1e-6)
    wins = []
    for L in range(2, MAXL + 1):
        for s in range(0, len(l) - L + 1):
            e = s + L
            inside = l[s:e]
            outside = np.r_[l[:max(0, s - 2)], l[min(len(l), e + 2):]]
            if len(outside) < 8:
                outside = np.r_[l[:s], l[e:]]
            m2 = np.median(outside); mad2 = np.median(np.abs(outside - m2))
            z = abs(inside.mean() - m2) / max(1.4826 * mad2, 1e-6) - 0.5 * L
            wins.append((float(z), s, L))
    return zf, wins


def detect(zf, wins, hi, lo, max_spans, merge_gap=2):
    seeds = sorted([(s, L, z) for z, s, L in wins if z >= hi], key=lambda x: x[0])
    clusters = []
    for s, L, z in seeds:
        e = s + L
        if clusters and s <= clusters[-1][1] + merge_gap:
            a, b, p = clusters[-1]
            clusters[-1] = (min(a, s), max(b, e), max(p, z))
        else:
            clusters.append((s, e, z))
    expanded = []
    for a, b, p in clusters:
        # limited expansion: at most 3 frames per side, avoids swallowing the sequence
        for _ in range(3):
            if a > 0 and zf[a - 1] >= lo:
                a -= 1
        for _ in range(3):
            if b < len(zf) and zf[b] >= lo:
                b += 1
        expanded.append((a, b, p))
    merged = []
    for a, b, p in sorted(expanded, key=lambda x: x[0]):
        if merged and a <= merged[-1][1] + merge_gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b), max(merged[-1][2], p))
        else:
            merged.append((a, b, p))
    merged.sort(key=lambda x: -x[2])
    chosen = []
    for a, b, p in merged:
        if any(not (b <= x or a >= y) for x, y, _ in chosen):
            continue
        chosen.append((a, b, p))
        if len(chosen) >= max_spans:
            break
    mask = np.zeros(len(zf), bool)
    for a, b, _ in chosen:
        mask[a:b] = True
    return mask, chosen


def evaluate(mask, intervals):
    union = np.zeros(76, bool)
    for s, L, *_ in intervals:
        union[s:s + L] = True
    tp = int((mask & union).sum()); fp = int((mask & ~union).sum()); fn = int((~mask & union).sum())
    hits = [1.0 if mask[s:s + L].sum() >= 0.5 * L else 0.0 for s, L, *_ in intervals]
    return tp / max(tp + fn, 1), tp / max(tp + fp, 1), hits


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    cache = {}
    for seq in SEQS:
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for key, intervals in TWO.items():
            inj_id = "A" if key.startswith("A") else "B"
            inj = ref
            for s, L in intervals:
                inj = apply_injection(inj, SPECS[inj_id], s, L).injected
            cache[("two", key, seq)] = scan(inj)
        for sc, intervals in THREE.items():
            inj = ref
            for s, L, inj_id in intervals:
                inj = apply_injection(inj, SPECS[inj_id], s, L).injected
            cache[("three", sc, seq)] = scan(inj)
    print("cached", len(cache), flush=True)

    his = [2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16]
    los = [0.5, 1, 1.5, 2, 3, 4, 6, 8]
    best = None
    for hi in his:
        for lo in los:
            if lo >= hi:
                continue
            for ms in (2, 3):
                vals = []
                for (ds, sc, seq), (zf, wins) in cache.items():
                    if ds != "two" or seq not in CFG["split"]["validation"]:
                        continue
                    mask, _ = detect(zf, wins, hi, lo, ms)
                    intervals = [(s, L, "A") for s, L in TWO[sc]]
                    r, p, _ = evaluate(mask, intervals)
                    vals.append((r, p))
                if not vals:
                    continue
                rec = np.mean([v[0] for v in vals]); pre = np.mean([v[1] for v in vals])
                f1 = 2 * rec * pre / max(rec + pre, 1e-9)
                if pre >= 0.40 and (best is None or f1 > best[5]):
                    best = (hi, lo, ms, rec, pre, f1)
    print("selected", best, flush=True)
    hi, lo, ms = best[0], best[1], best[2]

    rows = []
    for (ds, sc, seq), (zf, wins) in sorted(cache.items()):
        mask, chosen = detect(zf, wins, hi, lo, ms)
        if ds == "two":
            intervals = [(s, L, ("A" if sc.startswith("A") else "B")) for s, L in TWO[sc]]
            length = 4 if sc in ("A", "B") else 12
            inj = "A" if sc.startswith("A") else "B"
        else:
            intervals = THREE[sc]
            length = 0; inj = "mixed" if sc == "mixed" else "sameA"
        r, p, hits = evaluate(mask, intervals)
        hits += [0.0] * (3 - len(hits))
        rows.append({"dataset": ds, "scenario": sc,
                     "split": "validation" if seq in CFG["split"]["validation"] else "test",
                     "sequence": seq, "injection": inj, "length": length,
                     "hi": hi, "lo": lo, "max_spans": ms, "recall": r, "precision": p,
                     "hit1": hits[0], "hit2": hits[1], "hit3": hits[2], "n_spans": len(chosen),
                     "pred_spans": ";".join(f"{a}-{b}" for a, b, _ in chosen)})
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(ds, split, sc=None):
        rs = [r for r in rows if r["dataset"] == ds and r["split"] == split and (sc is None or r["scenario"] == sc)]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in ("recall", "precision", "hit1", "hit2", "hit3", "n_spans")}
    summary = {"run_id": "multi_merge_v1", "hi": hi, "lo": lo, "max_spans": ms,
               "two_test": agg("two", "test"),
               "three_test": agg("three", "test"), "three_test_mixed": agg("three", "test", "mixed"),
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
