"""Multi-interval detector: scan all windows, greedily select non-overlapping spans."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import cusum_alarm, cusum_score, prune_segments  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import luma_histogram  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
CFG = json.load(open(os.path.join(WS, "project", "configs", "rq3_threshold_v1.json"), encoding="utf-8"))
OUT = os.path.join(WS, "results", "runs", "multi_scan_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
MAXL = 24
FIELDS = ["split", "sequence", "injection", "len", "threshold", "recall", "precision",
          "hit1", "hit2", "n_spans", "pred_spans"]


def windows(frames):
    l = frame_luma_means(frames).astype(float)
    H = np.stack([luma_histogram(frames[t].astype(np.float32), 64) for t in range(len(frames))])
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


def select(ws, thr, max_spans=3):
    picked = []
    occupied = np.zeros(76, bool)
    for z, s, L in sorted(ws, key=lambda x: -x[0]):
        if z < thr:
            break
        if occupied[s:s + L].any():
            continue
        # avoid near-duplicates: require no overlap with a small guard
        picked.append((s, L)); occupied[max(0, s - 1):min(76, s + L + 1)] = True
        if len(picked) >= max_spans:
            break
    return picked, occupied


def evaluate(picked, occupied, intervals):
    union = np.zeros(76, bool)
    for s, L in intervals:
        union[s:s + L] = True
    tp = int((occupied & union).sum()); fp = int((occupied & ~union).sum()); fn = int((~occupied & union).sum())
    hits = []
    for s, L in intervals:
        cov = int(occupied[s:s + L].sum())
        hits.append(1.0 if cov >= 0.5 * L else 0.0)
    return tp / max(tp + fn, 1), tp / max(tp + fp, 1), hits


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    cache = {}
    for seq in SEQS:
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for L in (4, 12):
            for inj_id, spec in (("A", InjectionSpec("A", "offset", 20.0, -1)),
                                 ("B", InjectionSpec("B", "gamma", gamma=2.0))):
                inj = ref
                for s, _L in ((10, L), (50, L)):
                    inj = apply_injection(inj, spec, s, _L).injected
                cache[(seq, inj_id, L)] = windows(inj)
    print("cached", len(cache), flush=True)

    def split_of(seq):
        return "validation" if seq in CFG["split"]["validation"] else "test"

    grid = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20]
    best = None
    for thr in grid:
        rs = []
        for (seq, inj, L), ws in cache.items():
            if split_of(seq) != "validation":
                continue
            picked, occupied = select(ws, thr)
            r, p, _ = evaluate(picked, occupied, [(10, L), (50, L)])
            rs.append((r, p))
        rec = np.mean([x[0] for x in rs]); pre = np.mean([x[1] for x in rs])
        f1 = 2 * rec * pre / max(rec + pre, 1e-9)
        if pre >= 0.50 and (best is None or f1 > best[3]):
            best = (thr, rec, pre, f1)
    print("selected", best, flush=True)
    thr = best[0]

    rows = []
    for (seq, inj, L), ws in sorted(cache.items()):
        picked, occupied = select(ws, thr)
        r, p, hits = evaluate(picked, occupied, [(10, L), (50, L)])
        rows.append({"split": split_of(seq), "sequence": seq, "injection": inj, "len": L,
                     "threshold": thr, "recall": r, "precision": p,
                     "hit1": hits[0], "hit2": hits[1], "n_spans": len(picked),
                     "pred_spans": ";".join(f"{s}-{s+L}" for s, L in picked)})
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(split):
        rs = [r for r in rows if r["split"] == split]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in ("recall", "precision", "hit1", "hit2", "n_spans")}
    summary = {"run_id": "multi_scan_v1", "threshold": thr,
               "validation": agg("validation"), "test": agg("test"),
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
