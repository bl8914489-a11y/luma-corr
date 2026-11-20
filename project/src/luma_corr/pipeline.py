"""One experimental condition: inject -> correct -> measure.

The clean reference is used only inside this module's metric calls; correctors
receive ``injected`` plus the interval only.
"""
from __future__ import annotations

import time

import numpy as np

from .corrections import correct
from .imaging import frame_luma_means, luma, sha256_array_uint8
from .injection import InjectionSpec, apply_injection
from .metrics import frame_metrics, sequence_metrics


def run_condition(ref: np.ndarray, sequence: str, injection: InjectionSpec, start: int,
                  length: int, method: dict, window: int = 12,
                  l_ref: np.ndarray | None = None) -> tuple[list[dict], dict]:
    n = ref.shape[0]
    end = start + length
    t0 = time.perf_counter()
    inj = apply_injection(ref, injection, start, length)
    cres = correct(method, inj.injected, start, length)
    out = cres.out

    if l_ref is None:
        l_ref = frame_luma_means(ref)
    l_out = frame_luma_means(out)

    rows = []
    lo = max(0, start - window)
    hi = min(n, end + window)
    for t in range(lo, hi):
        ssim_on = (start - 3) <= t < (end + 3)
        y_out_t = luma(out[t].astype(np.float32))
        y_ref_t = luma(ref[t].astype(np.float32))
        fm = frame_metrics(out[t], ref[t], with_ssim=ssim_on, y_out=y_out_t, y_ref=y_ref_t)
        rows.append({
            "sequence": sequence, "injection": injection.id, "length": length,
            "method": method["id"], "scope": method.get("scope", "local"),
            "t": t, "in_interval": int(start <= t < end),
            **{k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in fm.items()},
        })

    interval_rows = [r for r in rows if r["in_interval"]]
    agg = sequence_metrics(out, ref, start, length, l_out, l_ref)
    dt = time.perf_counter() - t0
    summary = {
        "sequence": sequence, "injection": injection.id, "length": length,
        "method": method["id"], "scope": method.get("scope", "local"),
        "start": start, "end": end, "frames": n,
        "y_mae": float(np.mean([r["y_mae"] for r in interval_rows])),
        "rgb_mae": float(np.mean([r["rgb_mae"] for r in interval_rows])),
        "psnr": float(np.mean([r["psnr"] for r in interval_rows])),
        "ssim": float(np.mean([r["ssim"] for r in interval_rows])),
        "hist_dist": float(np.mean([r["hist_dist"] for r in interval_rows])),
        "injection_clip_fraction": inj.clip_fraction,
        "injection_mean_abs_diff": inj.magnitude_mean_abs_diff,
        "correction_clip_fraction": cres.info.get("clip_fraction", 0.0),
        "correction_offset_mean": cres.info.get("offset_mean", float("nan")),
        "target_kind": cres.info.get("target_kind", "identity"),
        "injected_interval_sha256": sha256_array_uint8(inj.injected[start:end]),
        "corrected_interval_sha256": sha256_array_uint8(out[start:end]),
        "runtime_s": dt,
        **agg,
    }
    return rows, summary
