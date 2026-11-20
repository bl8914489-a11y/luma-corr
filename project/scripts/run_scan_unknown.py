"""Length-agnostic scan detector: search all lengths 1..24, validation-only selection."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection_d1 import frame_metrics_from_mask, interval_metrics  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import luma_histogram  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
CFG = json.load(open(os.path.join(WS, "project", "configs", "rq3_threshold_v1.json"), encoding="utf-8"))
OUT = os.path.join(WS, "results", "runs", "rq3_scan_unknown_v1")
MAXL = 24
FIELDS = ["split", "sequence", "injection", "length", "variant", "lam", "threshold",
          "recall", "precision", "f1", "iou", "interval_hit", "pred_start", "pred_len", "score"]


def js(p, q):
    p = np.clip(p, 1e-9, None); p = p / p.sum()
    q = np.clip(q, 1e-9, None); q = q / q.sum()
    m = 0.5 * (p + q)
    return float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))


def scan(frames):
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
            hi = H[s:e].mean(axis=0)
            ho = np.r_[H[:max(0, s - 2)], H[min(len(H), e + 2):]]
            ho = ho.mean(axis=0) if len(ho) else H[:s].mean(axis=0)
            out.append((z, js(hi, ho) * np.sqrt(L), s, L))
    return out


def best(sc, variant, lam):
    b = (-1e9, 0, 0)
    for z, j, s, L in sc:
        v = {"luma": z, "js": j, "max": max(z, j * 50)}[variant] - lam * np.log(L)
        if v > b[0]:
            b = (float(v), s, L)
    return b


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    cache = {}
    for split, seqs in (("validation", CFG["split"]["validation"]), ("test", CFG["split"]["test"])):
        for seq in seqs:
            ref = load_frames(os.path.join(WS, "data", "frames", seq))
            for inj_id in ("A", "B", "B13"):
                spec = {"A": InjectionSpec("A", "offset", 20.0, -1),
                        "B": InjectionSpec("B", "gamma", gamma=2.0),
                        "B13": InjectionSpec("B13", "gamma", gamma=1.3)}[inj_id]
                for L in (1, 4, 12):
                    cache[(split, seq, inj_id, L)] = scan(apply_injection(ref, spec, 30, L).injected)
    print("cached", len(cache), flush=True)

    grid = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20]
    lambdas = [0.0, 0.1, 0.2, 0.4, 0.6]
    best_cfg = None
    for variant in ("luma", "js", "max"):
        for lam in lambdas:
            for thr in grid:
                vals = []
                for (split, seq, inj, L), sc in cache.items():
                    if split != "validation":
                        continue
                    score, s, predL = best(sc, variant, lam)
                    if score < thr:
                        s, predL = None, 0
                    m = np.zeros(76, bool)
                    if s is not None:
                        m[s:s + predL] = True
                    fm = frame_metrics_from_mask(m, 30, L)
                    vals.append((fm["recall"], fm["precision"], fm["f1"]))
                rec = np.mean([v[0] for v in vals]); pre = np.mean([v[1] for v in vals]); f1 = np.mean([v[2] for v in vals])
                if pre >= 0.60 and (best_cfg is None or f1 > best_cfg[4]):
                    best_cfg = (variant, lam, thr, (rec, pre, f1), f1)
    print("selected", best_cfg, flush=True)
    variant, lam, thr = best_cfg[0], best_cfg[1], best_cfg[2]

    rows = []
    for (split, seq, inj, L), sc in sorted(cache.items()):
        score, s, predL = best(sc, variant, lam)
        if score < thr:
            s, predL = None, 0
        m = np.zeros(76, bool)
        if s is not None:
            m[s:s + predL] = True
        fm = frame_metrics_from_mask(m, 30, L)
        im = interval_metrics([(s, s + predL)] if s is not None else [], 30, L)
        rows.append({"split": split, "sequence": seq, "injection": inj, "length": L,
                     "variant": variant, "lam": lam, "threshold": thr,
                     "recall": fm["recall"], "precision": fm["precision"], "f1": fm["f1"],
                     "iou": fm["iou"], "interval_hit": im["interval_hit"],
                     "pred_start": "" if s is None else s, "pred_len": predL, "score": score})
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(split, L):
        rs = [r for r in rows if r["split"] == split and r["length"] == L]
        return {k: float(np.mean([r[k] for r in rs])) for k in ("recall", "precision", "f1", "iou", "interval_hit")}
    summary = {"run_id": "rq3_scan_unknown_v1", "variant": variant, "lambda": lam, "threshold": thr,
               "validation": {f"len{L}": agg("validation", L) for L in (1, 4, 12)},
               "test": {f"len{L}": agg("test", L) for L in (1, 4, 12)},
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
