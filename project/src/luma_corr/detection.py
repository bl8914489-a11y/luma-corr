"""RQ3 defect-interval detectors.

Legacy detector
---------------
``median_dev``: |L(t) - median(L over a centred 7-frame window)| > 1.0.
It fails on persistent offsets because the local median is contaminated.

Proposed detector
-----------------
``hist_kl_cusum``:
1. 64-bin luma histogram per frame.
2. Jensen-Shannon divergence against the temporal-median histogram of a
   rolling 41-frame window (edge-clamped).  A defect shorter than half the
   window cannot move the median, while slow natural brightness drift is
   tracked.
3. Robust z-scores (median + 1.4826*MAD) of the JS divergence and of the
   absolute deviation of frame mean luma from the sequence median; the two
   z-scores are combined by maximum so that both histogram reshaping
   (gamma-like defects) and uniform level shifts (offset defects) are caught.
4. 3-frame moving average, then a one-sided CUSUM (k=0.5, h=6) accumulates
   sustained evidence; single-frame flicker does not alarm.
5. Segments shorter than 2 frames are removed.

No threshold uses ground-truth labels.  ``hist_kl`` (global-median baseline,
fixed robust threshold and hysteresis) is kept as an intermediate ablation.
"""
from __future__ import annotations

import numpy as np

from .imaging import frame_luma_means, luma
from .metrics import HIST_BINS, luma_histogram

EPS = 1e-9


def median_dev_score(frames: np.ndarray, window: int = 7) -> np.ndarray:
    l = frame_luma_means(frames)
    r = window // 2
    n = len(l)
    score = np.empty(n)
    for t in range(n):
        a, b = max(0, t - r), min(n, t + r + 1)
        score[t] = abs(l[t] - np.median(l[a:b]))
    return score


def hist_scores(frames: np.ndarray, bins: int = HIST_BINS, window: int | None = None
                ) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame histograms and Jensen-Shannon divergence to the baseline."""
    hs = np.stack([luma_histogram(luma(f.astype(np.float32)), bins) for f in frames])
    n = len(hs)
    js = np.empty(n)
    r = (window // 2) if window else 0
    for t in range(n):
        if window:
            base = np.median(hs[max(0, t - r):min(n, t + r + 1)], axis=0)
        else:
            base = np.median(hs, axis=0)
        b = np.clip(base, EPS, None)
        b /= b.sum()
        h = np.clip(hs[t], EPS, None)
        h /= h.sum()
        m = 0.5 * (h + b)
        js[t] = 0.5 * (float(np.sum(h * np.log(h / m))) + float(np.sum(b * np.log(b / m))))
    return hs, js


def _robust_z(x: np.ndarray) -> np.ndarray:
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))
    return (x - med) / max(1.4826 * mad, 1e-6)


def _smooth(score: np.ndarray, window: int = 3) -> np.ndarray:
    if window <= 1:
        return score.copy()
    r = window // 2
    n = len(score)
    out = np.empty(n)
    for t in range(n):
        out[t] = np.mean(score[max(0, t - r):min(n, t + r + 1)])
    return out


def cusum_score(frames: np.ndarray, bins: int = HIST_BINS, window: int = 41,
                smooth: int = 3) -> np.ndarray:
    """Stable score for the CUSUM detector: max(z_JS, z_luma), smoothed."""
    _, js = hist_scores(frames, bins, window)
    z_js = _robust_z(js)
    l = frame_luma_means(frames)
    z_luma = _robust_z(np.abs(l - np.median(l)))
    return _smooth(np.maximum(z_js, z_luma), smooth)


def dual_baseline_score(frames: np.ndarray, bins: int = HIST_BINS, window: int = 41,
                        smooth: int = 3) -> np.ndarray:
    """Max of rolling-median JS, global-median JS and luma deviation z-scores.

    The rolling baseline handles slow drift; the global baseline keeps a clean
    reference for sustained plateaus.  Taking the max gives each frame the
    stronger evidence of the two.
    """
    _, js_roll = hist_scores(frames, bins, window)
    _, js_glob = hist_scores(frames, bins, None)
    l = frame_luma_means(frames)
    z = np.maximum.reduce([
        _robust_z(js_roll),
        _robust_z(js_glob),
        _robust_z(np.abs(l - np.median(l))),
    ])
    return _smooth(z, smooth)


def hysteresis(score: np.ndarray, hi: float, lo: float, enter_n: int = 2, exit_n: int = 3) -> np.ndarray:
    n = len(score)
    mask = np.zeros(n, dtype=bool)
    active = False
    run_hi = run_lo = 0
    for t in range(n):
        if not active:
            run_hi = run_hi + 1 if score[t] >= hi else 0
            if run_hi >= enter_n:
                active = True
                mask[t - enter_n + 1:t + 1] = True
                run_lo = 0
        else:
            run_lo = run_lo + 1 if score[t] <= lo else 0
            if run_lo >= exit_n:
                active = False
                run_hi = 0
            else:
                mask[t] = True
    return mask


def cusum_alarm(z: np.ndarray, k: float = 0.5, h: float = 6.0) -> np.ndarray:
    mask = np.zeros(len(z), dtype=bool)
    c = 0.0
    for t in range(len(z)):
        c = max(0.0, c + z[t] - k)
        if c > h:
            mask[t] = True
            c = 0.5 * h
    return mask


def prune_segments(mask: np.ndarray, min_len: int = 2) -> np.ndarray:
    out = mask.copy()
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i < min_len:
                out[i:j] = False
            i = j
        else:
            i += 1
    return out


def _spans(mask: np.ndarray) -> list[tuple[int, int]]:
    idx = np.nonzero(mask)[0]
    spans = []
    if len(idx):
        a = idx[0]
        for i in range(1, len(idx)):
            if idx[i] != idx[i - 1] + 1:
                spans.append((int(a), int(idx[i - 1]) + 1))
                a = idx[i]
        spans.append((int(a), int(idx[-1]) + 1))
    return spans


def detect(frames: np.ndarray, method: dict) -> dict:
    kind = method["kind"]
    if kind == "median_dev":
        score = median_dev_score(frames, int(method.get("window", 7)))
        thr = float(method.get("threshold", 1.0))
        mask = score > thr
        return {"mask": mask, "score": score, "threshold_hi": thr, "threshold_lo": thr,
                "spans": _spans(mask), "params": {"threshold": thr}}
    if kind == "hist_kl":
        _, js = hist_scores(frames, int(method.get("bins", HIST_BINS)), None)
        sm = _smooth(js, int(method.get("smooth", 3)))
        z = float(method.get("z", 3.0))
        hi = float(np.median(sm) + z * 1.4826 * np.median(np.abs(sm - np.median(sm))))
        hi = max(hi, float(np.median(sm)) + 1e-6)
        lo = float(method.get("lo_ratio", 0.5)) * hi
        mask = hysteresis(sm, hi, lo, int(method.get("enter", 2)), int(method.get("exit", 3)))
        return {"mask": mask, "score": sm, "threshold_hi": hi, "threshold_lo": lo,
                "spans": _spans(mask), "params": {"z": z}}
    if kind == "hist_kl_cusum":
        window = int(method.get("window", 41))
        sm = cusum_score(frames, int(method.get("bins", HIST_BINS)), window,
                         int(method.get("smooth", 3)))
        k = float(method.get("k", 0.5))
        h = float(method.get("h", 6.0))
        mask = prune_segments(cusum_alarm(sm, k, h), int(method.get("min_len", 2)))
        return {"mask": mask, "score": sm, "threshold_hi": h, "threshold_lo": k,
                "spans": _spans(mask), "params": {"window": window, "k": k, "h": h,
                                                  "smooth": int(method.get("smooth", 3))}}
    raise ValueError(f"unknown detector kind {kind!r}")


def evaluate_detection(result: dict, start: int, length: int) -> dict:
    mask = result["mask"]
    n = len(mask)
    label = np.zeros(n, dtype=bool)
    label[start:start + length] = True
    tp = int(np.sum(mask & label))
    fp = int(np.sum(mask & ~label))
    fn = int(np.sum(~mask & label))
    recall = tp / max(tp + fn, 1)
    precision = tp / max(tp + fp, 1) if (tp + fp) else 0.0
    iou = tp / max(tp + fp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12) if (precision + recall) else 0.0
    span = result["spans"][0] if result["spans"] else None
    if span is None or length == 0:
        b_err = float("nan")
        delay = float("nan")
    else:
        b_err = 0.5 * (abs(span[0] - start) + abs(span[1] - (start + length)))
        delay = float(span[0] - start)
    return {"tp": tp, "fp": fp, "fn": fn, "recall": recall, "precision": precision,
            "iou": iou, "f1": f1, "detected_spans": result["spans"],
            "detected_span": span, "boundary_abs_error_mean": b_err,
            "start_delay": delay, "threshold_hi": result["threshold_hi"],
            "threshold_lo": result["threshold_lo"]}
