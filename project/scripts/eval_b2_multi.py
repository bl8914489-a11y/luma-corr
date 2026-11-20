"""Evaluate B2 All-In-One on the 52 two-interval cases against A1/A3/A7."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import boundary_metrics, frame_metrics  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
REPO = os.path.join(WS, "third_party", "All-In-One-Deflicker")
OUT = os.path.join(WS, "results", "runs", "b2_multi_v1")
SEQS = sorted(d for d in os.listdir(os.path.join(WS, "data", "frames"))
              if os.path.isdir(os.path.join(WS, "data", "frames", d)))
FIELDS = ["case", "sequence", "injection", "len", "method", "y_mae", "psnr", "ssim",
          "outfrac", "outside_rgb_mae", "boundary_err"]


def metrics(out, ref, intervals):
    lout = frame_luma_means(out); lref = frame_luma_means(ref)
    fm = []
    for s, L in intervals:
        fm += [frame_metrics(out[t], ref[t], with_ssim=True) for t in range(s, s + L)]
    outside = np.ones(len(ref), bool)
    for s, L in intervals:
        outside[s:s + L] = False
    diff = np.any(out != ref, axis=-1)
    bnd = sum(boundary_metrics(lout, lref, s, L)["boundary_jump_error_sum"] for s, L in intervals)
    return {"y_mae": float(np.mean([x["y_mae"] for x in fm])),
            "psnr": float(np.mean([x["psnr"] for x in fm])),
            "ssim": float(np.mean([x["ssim"] for x in fm])),
            "outfrac": float(diff[outside].mean()),
            "outside_rgb_mae": float(np.abs(out[outside].astype(float) - ref[outside].astype(float)).mean()),
            "boundary_err": float(bnd)}


def load_b2(case, n):
    d = os.path.join(REPO, "results", case, "final", "output")
    files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    if len(files) < n:
        raise FileNotFoundError((case, len(files)))
    return np.stack([np.asarray(Image.open(os.path.join(d, f)).convert("RGB"), dtype=np.uint8)
                     for f in files[:n]])


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
                out = {"A1": inj}
                for m in ("A3", "A7"):
                    cur = inj
                    for s, _L in intervals:
                        cur = correct({"id": m, "kind": "offset_linear" if m == "A3" else "gamma_adaptive",
                                       "k": 3, "scope": "local"}, cur, s, _L).out
                    out[m] = cur
                case = f"mi_{seq}_{inj_id}_len{L}"
                out["B2"] = load_b2(case, len(ref))
                for m, arr in out.items():
                    mm = metrics(arr, ref, intervals)
                    rows.append({"case": case, "sequence": seq, "injection": inj_id, "len": L,
                                 "method": m, **{k: round(v, 6) for k, v in mm.items()}})
        print(seq, flush=True)
    with open(os.path.join(OUT, "per_case.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    def agg(sel):
        rs = [r for r in rows if all(r[k] == v for k, v in sel.items())]
        return {k: float(np.mean([float(r[k]) for r in rs])) for k in
                ("y_mae", "psnr", "ssim", "outfrac", "outside_rgb_mae", "boundary_err")}
    summary = {"run_id": "b2_multi_v1", "n_cases": 52,
               "overall": {m: agg({"method": m}) for m in ("A1", "A3", "A7", "B2")},
               "len4": {m: agg({"method": m, "len": 4}) for m in ("A1", "A3", "A7", "B2")},
               "len12": {m: agg({"method": m, "len": 12}) for m in ("A1", "A3", "A7", "B2")},
               "environment": env_info(), "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary["overall"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
