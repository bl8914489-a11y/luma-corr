"""End-to-end: CUSUM predicted intervals -> local correction vs oracle interval."""
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
OUT = os.path.join(WS, "results", "runs", "e2e_detection_correction_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
SPECS = {"A": InjectionSpec("A", "offset", 20.0, -1), "B": InjectionSpec("B", "gamma", gamma=2.0),
         "B13": InjectionSpec("B13", "gamma", gamma=1.3)}
METHODS = {"A3": {"id": "A3", "kind": "offset_linear", "k": 3, "scope": "local"},
           "A7": {"id": "A7", "kind": "gamma_adaptive", "k": 3, "scope": "local"},
           "A7f": {"id": "A7f", "kind": "gamma_fixed", "gamma": 2.0, "scope": "local"},
           "A5": {"id": "A5", "kind": "ste", "scope": "local"}}
FIELDS = ["sequence", "injection", "len", "mode", "method", "det_recall", "det_precision", "n_spans",
          "y_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary_err"]


def spans_from_mask(mask):
    idx = np.nonzero(mask)[0]; out = []
    if len(idx):
        a = idx[0]
        for i in range(1, len(idx)):
            if idx[i] != idx[i - 1] + 1:
                out.append((a, idx[i - 1] + 1)); a = idx[i]
        out.append((a, idx[-1] + 1))
    return out


def apply_spans(inj, spans, cfg):
    cur = inj
    for a, b in spans:
        cur = correct(cfg, cur, a, b - a).out
    return cur


def metrics(out, ref, start, L):
    fm = [frame_metrics(out[t], ref[t], with_ssim=True) for t in range(start, start + L)]
    outside = np.ones(len(ref), bool); outside[start:start + L] = False
    diff = np.any(out != ref, axis=-1)
    bnd = boundary_metrics(frame_luma_means(out), frame_luma_means(ref), start, L)["boundary_jump_error_sum"]
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
        for inj_id, spec in SPECS.items():
            for L in (4, 12):
                start = 30
                inj = apply_injection(ref, spec, start, L).injected
                mask = prune_segments(cusum_alarm(cusum_score(inj), k=0.5, h=8.0), min_len=2)
                spans = spans_from_mask(mask)
                gt = np.zeros(len(ref), bool); gt[start:start + L] = True
                tp = int((mask & gt).sum()); fp = int((mask & ~gt).sum()); fn = int((~mask & gt).sum())
                rec = tp / max(tp + fn, 1); pre = tp / max(tp + fp, 1)
                for m, cfg in METHODS.items():
                    for mode in ("oracle", "detected"):
                        use = [(start, start + L)] if mode == "oracle" else spans
                        out = apply_spans(inj, use, cfg)
                        mm = metrics(out, ref, start, L)
                        rows.append({"sequence": seq, "injection": inj_id, "len": L, "mode": mode,
                                     "method": m, "det_recall": rec, "det_precision": pre,
                                     "n_spans": len(spans), **{k: round(v, 6) for k, v in mm.items()}})
        print(seq, flush=True)
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(sel):
        rs = [r for r in rows if all(r[k] == v for k, v in sel.items())]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in
                ("y_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary_err", "det_recall", "det_precision")}
    summary = {"run_id": "e2e_detection_correction_v1", "n_conditions": len(rows), "n_sequences": len(SEQS),
               "by_mode_method": {f"{mode}_{m}": agg({"mode": mode, "method": m})
                                  for mode in ("oracle", "detected") for m in METHODS},
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    for k, v in summary["by_mode_method"].items():
        print(k, "Y", round(v["y_mae"], 2), "out", round(v["outfrac"], 4), "R", round(v["det_recall"], 3))


if __name__ == "__main__":
    main()
