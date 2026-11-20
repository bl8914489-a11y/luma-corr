"""Four-interval defect stress test: correction and CUSUM detection."""
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
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import boundary_metrics, frame_metrics  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "results", "runs", "multi_four_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
SPECS = {"A": InjectionSpec("A", "offset", 20.0, -1), "B": InjectionSpec("B", "gamma", gamma=2.0),
         "B13": InjectionSpec("B13", "gamma", gamma=1.3)}
SCEN = {"mixed": [(6, 4, "A"), (24, 4, "B"), (42, 8, "B13"), (62, 8, "A")],
        "sameA": [(6, 4, "A"), (24, 4, "A"), (42, 8, "A"), (62, 8, "A")]}
FIELDS = ["scenario", "sequence", "method", "y_mae", "psnr", "ssim", "outfrac",
          "outside_rgb_mae", "boundary_err", "det_recall", "det_precision", "hit1", "hit2", "hit3", "hit4"]


def metrics(out, ref, intervals):
    lout = frame_luma_means(out); lref = frame_luma_means(ref)
    fm = []
    for s, L, _ in intervals:
        fm += [frame_metrics(out[t], ref[t], with_ssim=True) for t in range(s, s + L)]
    outside = np.ones(len(ref), bool)
    for s, L, _ in intervals:
        outside[s:s + L] = False
    diff = np.any(out != ref, axis=-1)
    bnd = sum(boundary_metrics(lout, lref, s, L)["boundary_jump_error_sum"] for s, L, _ in intervals)
    return {"y_mae": float(np.mean([x["y_mae"] for x in fm])),
            "psnr": float(np.mean([x["psnr"] for x in fm])),
            "ssim": float(np.mean([x["ssim"] for x in fm])),
            "outfrac": float(diff[outside].mean()),
            "outside_rgb_mae": float(np.abs(out[outside].astype(float) - ref[outside].astype(float)).mean()),
            "boundary_err": float(bnd)}


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    rows = []
    for seq in SEQS:
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for sc, intervals in SCEN.items():
            inj = ref
            for s, L, inj_id in intervals:
                inj = apply_injection(inj, SPECS[inj_id], s, L).injected
            outs = {"A1": inj}
            for m in ("A3", "A7"):
                cur = inj
                for s, L, _ in intervals:
                    cur = correct({"id": m, "kind": "offset_linear" if m == "A3" else "gamma_adaptive",
                                   "k": 3, "scope": "local"}, cur, s, L).out
                outs[m] = cur
            mask = prune_segments(cusum_alarm(cusum_score(inj), k=0.5, h=8.0), min_len=2)
            union = np.zeros(len(ref), bool)
            for s, L, _ in intervals:
                union[s:s + L] = True
            tp = int((mask & union).sum()); fp = int((mask & ~union).sum()); fn = int((~mask & union).sum())
            rec = tp / max(tp + fn, 1); pre = tp / max(tp + fp, 1)
            idx = np.nonzero(mask)[0]; spans = []
            if len(idx):
                a = idx[0]
                for i in range(1, len(idx)):
                    if idx[i] != idx[i - 1] + 1:
                        spans.append((a, idx[i - 1] + 1)); a = idx[i]
                spans.append((a, idx[-1] + 1))
            hits = [1.0 if sum(max(0, min(e, s + L) - max(a, s)) for a, e in spans) >= 0.5 * L else 0.0
                    for s, L, _ in intervals]
            for m, arr in outs.items():
                mm = metrics(arr, ref, intervals)
                rows.append({"scenario": sc, "sequence": seq, "method": m,
                             **{k: round(v, 6) for k, v in mm.items()},
                             "det_recall": rec, "det_precision": pre,
                             "hit1": hits[0], "hit2": hits[1], "hit3": hits[2], "hit4": hits[3]})
        print(seq, flush=True)
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(sc, m):
        rs = [r for r in rows if r["scenario"] == sc and r["method"] == m]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in
                ("y_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary_err",
                 "det_recall", "det_precision", "hit1", "hit2", "hit3", "hit4")}
    summary = {"run_id": "multi_four_v1", "n_conditions": len(rows), "n_sequences": len(SEQS),
               "scenarios": {k: [[s, L, i] for s, L, i in v] for k, v in SCEN.items()},
               "by_scenario_method": {f"{sc}_{m}": agg(sc, m) for sc in SCEN for m in ("A1", "A3", "A7")},
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    for k, v in summary["by_scenario_method"].items():
        print(k, round(v["y_mae"], 2), round(v["det_recall"], 2), round(v["hit1"], 2), round(v["hit4"], 2))


if __name__ == "__main__":
    main()
