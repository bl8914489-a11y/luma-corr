"""Deterministic brightness-correction baselines (Tier A).

Every corrector receives only the *injected* sequence and the interval; the
clean reference is never visible to it.  Corrections are applied as a global
per-frame additive offset in RGB (which preserves chromaticity), as a luma tone
curve, or as a temporal content filter.  The ``scope`` field decides whether
frames outside the interval may be touched:

* ``local``  - only frames in ``[start, start+length)`` are written back;
* ``global`` - every frame is written back (used for the RQ2 ablation).

Methods
-------
A1  noop                       identity
A2  local_median_7             median luma of a centred 7-frame window
A3  local_outside_linear_k3    least-squares line through k=3 clean frames each side
A4  full_sequence_median_7     A2 estimator, global write-back
A5  ste_hist_spec              scale-time-equalisation style histogram specification
                               against the clean context histogram
A6  clahe                      per-frame CLAHE on luma, local write-back
A7  gamma_adaptive             per-frame gamma that matches the A3 target luma
A7f gamma_fixed_inv2           fixed inverse gamma 2.0 (reference)
A8  temporal_bilateral         bilateral filter along time, guided by the window median
A9  kalman_luma                1-D Kalman/RTS luma trend with the interval treated as missing
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .imaging import frame_luma_means, luma, to_uint8


@dataclass
class CorrectionResult:
    out: np.ndarray
    info: dict = field(default_factory=dict)


def _means(frames):
    return frame_luma_means(frames)


def _clamped_median_target(l_means: np.ndarray, radius: int) -> np.ndarray:
    n = len(l_means)
    out = np.empty(n, dtype=np.float64)
    for t in range(n):
        a = max(0, t - radius)
        b = min(n, t + radius + 1)
        out[t] = np.median(l_means[a:b])
    return out


def _linear_context_target(l_means: np.ndarray, start: int, length: int, k: int) -> np.ndarray:
    """Least-squares line fitted on k frames before and k frames after the interval."""
    n = len(l_means)
    if start - k < 0 or start + length + k > n:
        k = max(0, min(start, n - (start + length), k))
    xs = np.concatenate([np.arange(start - k, start), np.arange(start + length, start + length + k)])
    ys = l_means[xs]
    if len(xs) == 0:
        return np.full(length, np.mean(l_means))
    if len(xs) == 1:
        return np.full(length, ys[0])
    coef = np.polyfit(xs, ys, 1)
    return np.polyval(coef, np.arange(start, start + length))


def _linear_context_target_edge(l_means: np.ndarray, start: int, length: int, k: int) -> np.ndarray:
    """Edge-aware variant: if one side has no context, extrapolate from the other side.

    At start=0 (or an interval ending at the last frame) the original A3 falls
    back to a constant equal to the whole-sequence mean, which includes the
    defect.  Here we fit up to 2k frames from the available side and extrapolate.
    """
    n = len(l_means)
    left = np.arange(max(0, start - k), start)
    right = np.arange(start + length, min(n, start + length + k))
    if len(left) == 0 and len(right) == 0:
        return np.full(length, np.median(l_means))
    if len(left) == 0:
        xs = right[: 2 * k]
    elif len(right) == 0:
        xs = left[-2 * k:]
    else:
        xs = np.concatenate([left, right])
    ys = l_means[xs]
    if len(xs) == 1:
        return np.full(length, ys[0])
    coef = np.polyfit(xs, ys, 1)
    return np.polyval(coef, np.arange(start, start + length))


def _apply_offsets(frames: np.ndarray, targets: np.ndarray, scope: np.ndarray,
                   l_means: np.ndarray, soft_knee: float = 0.0) -> tuple[np.ndarray, dict]:
    """Add one scalar offset per frame to every RGB pixel of frames in ``scope``.

    ``soft_knee`` > 0 replaces hard upper clipping by a tanh shoulder starting
    at that value, so highlight information is compressed instead of discarded.
    """
    out = frames.copy()
    clipped = 0
    total = 0
    for t in np.nonzero(scope)[0]:
        delta = float(targets[t] - l_means[t])
        block = frames[t].astype(np.float64) + delta
        if soft_knee > 0.0:
            hi = block > soft_knee
            span = 255.0 - soft_knee
            block[hi] = soft_knee + span * np.tanh((block[hi] - soft_knee) / span)
        clipped += int(np.sum((block < 0.0) | (block > 255.0)))
        total += block.size
        out[t] = to_uint8(block)
    return out, {"clip_fraction": clipped / max(total, 1), "clipped_channels": clipped,
                 "offset_mean": float(np.mean([targets[t] - l_means[t] for t in np.nonzero(scope)[0]]))}


def _scope_array(n: int, start: int, length: int, scope: str) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    if scope == "global":
        m[:] = True
    else:
        m[start:start + length] = True
    return m


def _clahe_luma(y: np.ndarray, tiles: int, clip_limit: float) -> np.ndarray:
    """CLAHE on a 2-D uint8 luma plane with bilinear interpolation between tiles."""
    h, w = y.shape
    ty = max(1, h // tiles)
    tx = max(1, w // tiles)
    maps = np.empty((tiles, tiles, 256), dtype=np.uint8)
    for gy in range(tiles):
        y0, y1 = gy * ty, h if gy == tiles - 1 else (gy + 1) * ty
        for gx in range(tiles):
            x0, x1 = gx * tx, w if gx == tiles - 1 else (gx + 1) * tx
            block = y[y0:y1, x0:x1]
            hist = np.bincount(block.ravel(), minlength=256).astype(np.float64)
            if clip_limit > 0:
                limit = clip_limit * block.size / 256.0
                excess = np.maximum(hist - limit, 0.0)
                hist = np.minimum(hist, limit)
                hist += excess.sum() / 256.0
            cdf = np.cumsum(hist)
            cdf /= cdf[-1] if cdf[-1] > 0 else 1.0
            maps[gy, gx] = np.clip(np.round(cdf * 255.0), 0, 255).astype(np.uint8)
    ys = np.linspace(0, h - 1, tiles)
    xs = np.linspace(0, w - 1, tiles)
    py = np.arange(h)
    px = np.arange(w)
    gy0 = np.clip(np.searchsorted(ys, py, side="right") - 1, 0, tiles - 1)
    gx0 = np.clip(np.searchsorted(xs, px, side="right") - 1, 0, tiles - 1)
    gy1 = np.clip(gy0 + 1, 0, tiles - 1)
    gx1 = np.clip(gx0 + 1, 0, tiles - 1)
    wy = np.where(gy1 > gy0, (py - ys[gy0]) / np.maximum(ys[gy1] - ys[gy0], 1e-9), 0.0)[:, None]
    wx = np.where(gx1 > gx0, (px - xs[gx0]) / np.maximum(xs[gx1] - xs[gx0], 1e-9), 0.0)[None, :]
    v = y.astype(np.int64)
    m00 = maps[gy0[:, None], gx0[None, :], v]
    m01 = maps[gy0[:, None], gx1[None, :], v]
    m10 = maps[gy1[:, None], gx0[None, :], v]
    m11 = maps[gy1[:, None], gx1[None, :], v]
    top = m00 * (1 - wx) + m01 * wx
    bot = m10 * (1 - wx) + m11 * wx
    return np.clip(top * (1 - wy) + bot * wy, 0, 255)


def _hist_spec_map(y: np.ndarray, ref_hist: np.ndarray) -> np.ndarray:
    """256-entry monotone mapping taking the histogram of y towards ref_hist."""
    hist = np.bincount(y.ravel(), minlength=256).astype(np.float64)
    cdf_src = np.cumsum(hist)
    if cdf_src[-1] <= 0:
        return np.arange(256, dtype=np.uint8)
    cdf_src /= cdf_src[-1]
    ref = ref_hist.astype(np.float64)
    cdf_ref = np.cumsum(ref)
    cdf_ref /= cdf_ref[-1] if cdf_ref[-1] > 0 else 1.0
    levels = np.arange(256, dtype=np.float64)
    idx = np.searchsorted(cdf_ref, cdf_src, side="left")
    return np.clip(idx, 0, 255).astype(np.uint8)


def _apply_luma_delta(frames: np.ndarray, t: int, y_new: np.ndarray) -> tuple[np.ndarray, int]:
    """Add the luma difference (y_new - y) equally to R, G and B (chroma-preserving)."""
    y = luma(frames[t].astype(np.float32)).astype(np.float64)
    delta = y_new - y
    block = frames[t].astype(np.float64) + delta[..., None]
    clipped = int(np.sum((block < 0.0) | (block > 255.0)))
    return block, clipped


def _gamma_to_target(y: np.ndarray, target_mean: float) -> float:
    """Solve mean(255*(y/255)^g) = target_mean for g, via bisection."""
    yn = np.clip(y.astype(np.float64) / 255.0, 0.0, 1.0)
    target = float(np.clip(target_mean, 1e-6, 255.0))

    def f(g: float) -> float:
        return float((255.0 * np.power(yn, g)).mean() - target)

    lo, hi = 0.05, 6.0
    if f(lo) < 0:
        return lo
    if f(hi) > 0:
        return hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def correct(method: dict, frames: np.ndarray, start: int, length: int) -> CorrectionResult:
    """Apply one correction method to an injected sequence."""
    mid = method["id"]
    kind = method["kind"]
    scope = method.get("scope", "local")
    n = frames.shape[0]
    end = start + length
    mask = _scope_array(n, start, length, scope)

    if kind == "noop":
        return CorrectionResult(frames.copy(), {"clip_fraction": 0.0, "clipped_channels": 0,
                                                "offset_mean": 0.0})

    if kind == "offset_median":
        l_means = _means(frames)
        radius = int(method.get("window", 7)) // 2
        targets = _clamped_median_target(l_means, radius)
        out, info = _apply_offsets(frames, targets, mask, l_means, float(method.get("soft_knee", 0.0)))
        info.update({"target_kind": "local_median", "window": 2 * radius + 1})
        return CorrectionResult(out, info)

    if kind == "offset_linear":
        l_means = _means(frames)
        k = int(method.get("k", 3))
        targets = np.full(n, np.nan)
        targets[start:end] = _linear_context_target(l_means, start, length, k)
        # only interval frames are targeted for local scope
        out, info = _apply_offsets(frames, targets, mask, l_means, float(method.get("soft_knee", 0.0)))
        info.update({"target_kind": "outside_linear", "k": k})
        return CorrectionResult(out, info)

    if kind == "offset_linear_edge":
        l_means = _means(frames)
        k = int(method.get("k", 3))
        targets = np.full(n, np.nan)
        targets[start:end] = _linear_context_target_edge(l_means, start, length, k)
        out, info = _apply_offsets(frames, targets, mask, l_means, float(method.get("soft_knee", 0.0)))
        info.update({"target_kind": "outside_linear_edge", "k": k})
        return CorrectionResult(out, info)

    if kind == "ste":
        ctx = int(method.get("context", 5))
        idx = [i for i in range(max(0, start - ctx), min(n, end + ctx)) if not (start <= i < end)]
        if not idx:
            idx = [i for i in range(n) if not (start <= i < end)]
        ref_hist = np.zeros(256, dtype=np.float64)
        for i in idx:
            ref_hist += np.bincount(luma(frames[i].astype(np.float64)).astype(np.uint8).ravel(), minlength=256)
        ref_hist /= max(ref_hist.sum(), 1.0)
        out = frames.copy()
        clipped = 0
        total = 0
        for t in range(start, end):
            y = luma(frames[t].astype(np.float32))
            y8 = np.clip(np.rint(y), 0, 255).astype(np.uint8)
            m = _hist_spec_map(y8, ref_hist)
            y_new = m[y8].astype(np.float64)
            block, c = _apply_luma_delta(frames, t, y_new)
            clipped += c
            total += block.size
            out[t] = to_uint8(block)
        return CorrectionResult(out, {"clip_fraction": clipped / max(total, 1), "clipped_channels": clipped,
                                      "offset_mean": float("nan"), "target_kind": "ste_hist_spec"})

    if kind == "clahe":
        tiles = int(method.get("tiles", 8))
        clip_limit = float(method.get("clip_limit", 2.0))
        out = frames.copy()
        clipped = 0
        total = 0
        for t in range(start, end):
            y = luma(frames[t].astype(np.float32))
            y8 = np.clip(np.rint(y), 0, 255).astype(np.uint8)
            y_new = _clahe_luma(y8, tiles, clip_limit).astype(np.float64)
            block, c = _apply_luma_delta(frames, t, y_new)
            clipped += c
            total += block.size
            out[t] = to_uint8(block)
        return CorrectionResult(out, {"clip_fraction": clipped / max(total, 1), "clipped_channels": clipped,
                                      "offset_mean": float("nan"), "target_kind": "clahe",
                                      "tiles": tiles, "clip_limit": clip_limit})

    if kind == "gamma_adaptive":
        l_means = _means(frames)
        targets = _linear_context_target(l_means, start, length, int(method.get("k", 3)))
        out = frames.copy()
        gammas = []
        clipped = 0
        total = 0
        for i, t in enumerate(range(start, end)):
            y = luma(frames[t].astype(np.float32))
            g = _gamma_to_target(y, targets[i])
            gammas.append(g)
            y_new = 255.0 * np.power(np.clip(y.astype(np.float64) / 255.0, 0.0, 1.0), g)
            block, c = _apply_luma_delta(frames, t, y_new)
            clipped += c
            total += block.size
            out[t] = to_uint8(block)
        return CorrectionResult(out, {"clip_fraction": clipped / max(total, 1), "clipped_channels": clipped,
                                      "offset_mean": float("nan"), "target_kind": "gamma_adaptive",
                                      "gammas": gammas})

    if kind == "gamma_fixed":
        g = float(method.get("gamma", 2.0))
        out = frames.copy()
        clipped = 0
        total = 0
        for t in range(start, end):
            y = luma(frames[t].astype(np.float32))
            y_new = 255.0 * np.power(np.clip(y.astype(np.float64) / 255.0, 0.0, 1.0), 1.0 / g)
            block, c = _apply_luma_delta(frames, t, y_new)
            clipped += c
            total += block.size
            out[t] = to_uint8(block)
        return CorrectionResult(out, {"clip_fraction": clipped / max(total, 1), "clipped_channels": clipped,
                                      "offset_mean": float("nan"), "target_kind": "gamma_fixed",
                                      "gamma": g})

    if kind == "bilateral":
        radius = int(method.get("window", 7)) // 2
        sigma_r = float(method.get("sigma_r", 8.0))
        sigma_t = float(method.get("sigma_t", 2.0))
        out = frames.copy()
        for t in range(start, end):
            a, b = max(0, t - radius), min(n, t + radius + 1)
            stack = frames[a:b].astype(np.float64)
            ys = luma(stack)
            guide = np.median(ys, axis=0)
            tt = np.arange(a, b)
            w_t = np.exp(-((tt - t) ** 2) / (2 * sigma_t ** 2))
            w_r = np.exp(-((ys - guide[None, :, :]) ** 2) / (2 * sigma_r ** 2))
            w = w_r * w_t[:, None, None]
            wsum = w.sum(axis=0)
            acc = np.sum(w[..., None] * stack, axis=0)
            out[t] = to_uint8(acc / np.maximum(wsum[..., None], 1e-9))
        return CorrectionResult(out, {"clip_fraction": 0.0, "clipped_channels": 0,
                                      "offset_mean": float("nan"), "target_kind": "bilateral"})

    if kind == "kalman":
        q = float(method.get("q", 0.05))
        r = float(method.get("r", 2.0))
        l_means = _means(frames)
        x = np.zeros(n)
        P = np.zeros(n)
        x[0], P[0] = l_means[0], 1.0
        for t in range(1, n):
            xp = x[t - 1]
            pp = P[t - 1] + q
            if start <= t < end:
                x[t], P[t] = xp, pp
            else:
                k = pp / (pp + r)
                x[t] = xp + k * (l_means[t] - xp)
                P[t] = (1.0 - k) * pp
        xs = x.copy()
        for t in range(n - 2, -1, -1):
            pp = P[t] + q
            c = P[t] / pp if pp > 0 else 0.0
            xs[t] = x[t] + c * (xs[t + 1] - x[t])
        targets = np.full(n, np.nan)
        targets[start:end] = xs[start:end]
        out, info = _apply_offsets(frames, targets, mask, l_means, float(method.get("soft_knee", 0.0)))
        info.update({"target_kind": "kalman_rts", "q": q, "r": r})
        return CorrectionResult(out, info)

    raise ValueError(f"unknown correction kind {kind!r}")
