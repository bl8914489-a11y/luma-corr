"""D1/D2 detector experiments requested by the novelty report (Section 5).

D1 is a faithful reimplementation of the histogram-based flicker score used by
BlazeBVD Eq. (5): temporally Gaussian-smoothed illumination histograms, a
KL/JS divergence between the smoothed and the original histogram, and a local
sliding-mean threshold.  It is a *baseline*, not a contribution.

D2 turns a frame score into intervals: dual threshold, minimum duration, gap
merging and change-point boundary refinement.  The novelty claim can only live
in D2 + interval-level evaluation + the detection-to-correction link.

Everything is deterministic NumPy; no network, no weights.
"""
from __future__ import annotations

import numpy as np

from .imaging import frame_luma_means, luma
from .metrics import luma_histogram

EPS = 1e-9


# ---------------------------------------------------------------- histograms
def hist_stack(frames: np.ndarray, bins: int = 64) -> np.ndarray:
    return np.stack([luma_histogram(luma(f.astype(np.float32)), bins) for f in frames])


def gaussian_kernel(sigma: float) -> np.ndarray:
    sigma = max(float(sigma), 1e-3)
    radius = max(1, int(round(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-(x * x) / (2.0 * sigma * sigma))
    return k / k.sum()


def smooth_time(H: np.ndarray, sigma: float) -> np.ndarray:
    k = gaussian_kernel(sigma)
    r = len(k) // 2
    pad = np.pad(H, ((r, r), (0, 0)), mode="edge")
    out = np.zeros_like(H)
    n = H.shape[0]
    for i, ki in enumerate(k):
        out += ki * pad[i:i + n]
    return out


def _norm(H: np.ndarray) -> np.ndarray:
    H = np.clip(H, EPS, None)
    return H / H.sum(axis=1, keepdims=True)


def kl_rows(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    p, q = _norm(p), _norm(q)
    return np.sum(p * np.log(p / q), axis=1)


def js_rows(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    p, q = _norm(p), _norm(q)
    m = 0.5 * (p + q)
    return 0.5 * np.sum(p * np.log(p / m), axis=1) + 0.5 * np.sum(q * np.log(q / m), axis=1)


# ---------------------------------------------------------------- D1 score
def d1_score(H: np.ndarray, sigma: float = 2.0, mode: str = "kl") -> np.ndarray:
    Hs = smooth_time(H, sigma)
    if mode == "kl":
        return kl_rows(Hs, H)
    if mode == "js":
        return js_rows(Hs, H)
    raise ValueError(mode)


def local_mean(x: np.ndarray, radius: int = 5) -> np.ndarray:
    n = len(x)
    out = np.empty(n)
    for t in range(n):
        out[t] = np.mean(x[max(0, t - radius):min(n, t + radius + 1)])
    return out


def eq5_mask(score: np.ndarray, neighbors: int = 5, alpha: float = 1.0) -> np.ndarray:
    """BlazeBVD Eq.(5)-style rule: s_t > alpha * local_mean(s)."""
    thr = local_mean(score, neighbors)
    return score > alpha * np.maximum(thr, EPS)


# ---------------------------------------------------------------- spans / D2
def spans_from_mask(mask: np.ndarray) -> list[tuple[int, int]]:
    idx = np.nonzero(mask)[0]
    if len(idx) == 0:
        return []
    spans = []
    a = idx[0]
    for i in range(1, len(idx)):
        if idx[i] != idx[i - 1] + 1:
            spans.append((int(a), int(idx[i - 1]) + 1))
            a = idx[i]
    spans.append((int(a), int(idx[-1]) + 1))
    return spans


def _merge(spans: list[tuple[int, int]], max_gap: int) -> list[tuple[int, int]]:
    if not spans:
        return []
    spans = sorted(spans)
    out = [spans[0]]
    for a, b in spans[1:]:
        pa, pb = out[-1]
        if a - pb <= max_gap:
            out[-1] = (pa, max(pb, b))
        else:
            out.append((a, b))
    return out


def _refine(span: tuple[int, int], luma_means: np.ndarray, radius: int = 2) -> tuple[int, int]:
    n = len(luma_means)
    a, b = span
    d = np.abs(np.diff(luma_means))  # d[t] = |L[t+1]-L[t]|, change point at t+1
    best_a, best_va = a, -1.0
    for cand in range(max(1, a - radius), min(n, a + radius + 1)):
        v = d[cand - 1]
        if v > best_va:
            best_a, best_va = cand, v
    best_b, best_vb = b, -1.0
    for cand in range(max(1, b - radius), min(n, b + radius + 1)):
        v = d[cand - 1]
        if v > best_vb:
            best_b, best_vb = cand, v
    if best_b <= best_a:
        best_b = best_a + 1
    return int(best_a), int(min(best_b, n))


def d2_spans(score: np.ndarray, hi: float, lo: float, luma_means: np.ndarray | None = None,
             min_len: int = 2, max_gap: int = 2, expand: bool = True,
             refine: bool = True) -> list[tuple[int, int]]:
    n = len(score)
    seeds = score >= hi
    mask = seeds.copy()
    if expand:
        for a, b in spans_from_mask(seeds):
            left = a
            while left > 0 and score[left - 1] >= lo:
                left -= 1
            right = b
            while right < n and score[right] >= lo:
                right += 1
            mask[left:right] = True
    spans = _merge(spans_from_mask(mask), max_gap)
    spans = [(a, b) for a, b in spans if b - a >= min_len]
    if refine and luma_means is not None:
        spans = [_refine(s, luma_means) for s in spans]
    return spans


def robust_threshold(score: np.ndarray, k: float = 3.0) -> float:
    hi, _ = robust_parts(score, k)
    return hi


def robust_parts(score: np.ndarray, k: float = 3.0) -> tuple[float, float]:
    med = float(np.median(score))
    mad = float(np.median(np.abs(score - med)))
    hi = max(med + k * 1.4826 * mad, med + 1e-6)
    return hi, med


# ---------------------------------------------------------------- evaluation
def frame_metrics_from_mask(mask: np.ndarray, start: int, length: int) -> dict:
    label = np.zeros(len(mask), dtype=bool)
    label[start:start + length] = True
    tp = int((mask & label).sum()); fp = int((mask & ~label).sum()); fn = int((~mask & label).sum())
    r = tp / max(tp + fn, 1)
    p = tp / max(tp + fp, 1) if (tp + fp) else 0.0
    iou = tp / max(tp + fp + fn, 1)
    f1 = 2 * p * r / max(p + r, 1e-12) if (p + r) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "recall": r, "precision": p, "iou": iou, "f1": f1,
            "fp_rate": fp / max(len(mask), 1)}


def interval_metrics(spans: list[tuple[int, int]], start: int, length: int) -> dict:
    if not spans or length <= 0:
        return {"interval_iou": float("nan"), "interval_hit": 0.0, "n_spans": len(spans),
                "span_start": None, "span_end": None, "boundary_err": float("nan")}
    best = None
    best_iou = -1.0
    for a, b in spans:
        inter = max(0, min(b, start + length) - max(a, start))
        union = max(b, start + length) - min(a, start)
        iou = inter / union if union > 0 else 0.0
        if iou > best_iou:
            best_iou, best = iou, (a, b)
    a, b = best
    boundary = 0.5 * (abs(a - start) + abs(b - (start + length)))
    return {"interval_iou": float(best_iou), "interval_hit": float(best_iou >= 0.5),
            "n_spans": len(spans), "span_start": a, "span_end": b, "boundary_err": float(boundary)}


def pr_curve(score: np.ndarray, start: int, length: int, n_points: int = 40) -> tuple[list, float]:
    """Frame-level precision/recall sweep and average precision for one condition."""
    label = np.zeros(len(score), dtype=bool)
    label[start:start + length] = True
    lo, hi = float(np.min(score)), float(np.max(score))
    if not np.isfinite(lo) or hi <= lo:
        return [], 0.0
    thrs = np.linspace(lo, hi, n_points)
    pts = []
    for thr in thrs:
        mask = score > thr
        tp = int((mask & label).sum()); fp = int((mask & ~label).sum()); fn = int((~mask & label).sum())
        r = tp / max(tp + fn, 1); p = tp / max(tp + fp, 1) if (tp + fp) else 0.0
        pts.append((float(thr), r, p))
    # average precision: integrate precision over recall
    pts_sorted = sorted([(r, p) for _, r, p in pts if r > 0], key=lambda x: x[0])
    ap = 0.0
    prev_r = 0.0
    for r, p in pts_sorted:
        ap += (r - prev_r) * p
        prev_r = r
    return pts, float(ap)
