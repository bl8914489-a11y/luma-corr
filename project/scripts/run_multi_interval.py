"""Two-interval defect experiment: detection and correction on disjoint defects."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.detection import cusum_alarm, cusum_score, prune_segments  # noqa: E402
from luma_corr.detection_d1 import frame_metrics_from_mask  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import boundary_metrics, frame_metrics  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "results", "runs", "multi_interval_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
FIELDS = ["sequence", "injection", "len", "method", "y_mae", "psnr", "ssim",
          "outfrac", "outside_rgb_mae", "boundary_err", "det_recall", "det_precision",
          "hit1", "hit2", "n_spans"]


def metrics_two(out, ref, intervals):
    lout = frame_luma_means(out); lref = frame_luma_means(ref)
    fm = []
    for s, L in intervals:
        fm += [frame_metrics(out[t], ref[t], with_ssim=True) for t in range(s, s + L)]
    outside = np.ones(len(ref), bool)
    for s, L in intervals:
        outside[s:s + L] = False
    diff = np.any(out != ref, axis=-1)
    bnd = sum(boundary_metrics(lout, lref, s, L)["boundary_jump_error_sum"] for s, L in intervals)
    return {
        "y_mae": float(np.mean([x["y_mae"] for x in fm])),
        "psnr": float(np.mean([x["psnr"] for x in fm])),
        "ssim": float(np.mean([x["ssim"] for x in fm])),
        "outfrac": float(diff[outside].mean()),
        "outside_rgb_mae": float(np.abs(out[outside].astype(float) - ref[outside].astype(float)).mean()),
        "boundary_err": float(bnd),
    }


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    rows = []
    for seq in SEQS:
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for L in (4, 12):
            intervals = [(10, L), (50, L)]
            for inj_id, spec in (("A", InjectionSpec("A", "offset", 20.0, -1)),
                                 ("B", InjectionSpec("B", "gamma", gamma=2.0))):
                inj = ref
                for s, _L in intervals:
                    inj = apply_injection(inj, spec, s, _L).injected
                outs = {"A1": inj, "A3": inj, "A7": inj}
                for name in ("A3", "A7"):
                    cur = inj
                    for s, _L in intervals:
                        cur = correct({"id": name, "kind": "offset_linear" if name == "A3" else "gamma_adaptive",
                                       "k": 3, "scope": "local"}, cur, s, _L).out
                    outs[name] = cur
                score = cusum_score(inj)
                mask = prune_segments(cusum_alarm(score, k=0.5, h=8.0), min_len=2)
                union = np.zeros(len(ref), bool)
                for s, _L in intervals:
                    union[s:s + _L] = True
                tp = int((mask & union).sum()); fp = int((mask & ~union).sum()); fn = int((~mask & union).sum())
                det = {"recall": tp / max(tp + fn, 1), "precision": tp / max(tp + fp, 1)}
                # per-interval hit: >=50% of the interval covered by any span
                idx = np.nonzero(mask)[0]
                spans = []
                if len(idx):
                    a = idx[0]
                    for i in range(1, len(idx)):
                        if idx[i] != idx[i - 1] + 1:
                            spans.append((a, idx[i - 1] + 1)); a = idx[i]
                    spans.append((a, idx[-1] + 1))
                hits = []
                for s, _L in intervals:
                    cov = sum(max(0, min(e, s + _L) - max(a, s)) for a, e in spans)
                    hits.append(1.0 if cov >= 0.5 * _L else 0.0)
                for method, out in outs.items():
                    m = metrics_two(out, ref, intervals)
                    rows.append({"sequence": seq, "injection": inj_id, "len": L, "method": method,
                                 **{k: round(v, 6) for k, v in m.items()},
                                 "det_recall": det["recall"], "det_precision": det["precision"],
                                 "hit1": hits[0], "hit2": hits[1], "n_spans": len(spans)})
        print(seq, flush=True)
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

    def mean(sel):
        rs = [r for r in rows if all(r[k] == v for k, v in sel.items())]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in
                ("y_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary_err", "det_recall", "det_precision", "hit1", "hit2")}
    summary = {"run_id": "multi_interval_v1", "n_conditions": len(rows), "n_sequences": len(SEQS),
               "intervals": [[10, 14], [50, 54]], "note": "len in {4,12}; second interval shifts with len",
               "by_len_inj_method": {f"{L}_{inj}_{m}": mean({"len": str(L), "injection": inj, "method": m})
                                     for L in (4, 12) for inj in ("A", "B") for m in ("A1", "A3", "A7")},
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1)[:2000])


if __name__ == "__main__":
    main()
