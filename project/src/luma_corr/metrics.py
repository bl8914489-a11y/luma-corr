"""Evaluation metrics.

Design notes
------------
* Reconstruction error is measured on BT.601 luma (``y_mae``) and on RGB
  channels (``rgb_mae``); PSNR uses RGB MSE; SSIM uses luma with a 9x9 uniform
  window (integral-image box filter) and the standard constants
  C1=(0.01*255)^2, C2=(0.03*255)^2.
* Region preservation uses the fraction of *pixels* outside the defect
  interval whose RGB values changed at all, plus the outside RGB MAE.
* Boundary error is reported as a total jump error and decomposed into
  ``estimator_bias`` (level error on the two boundary frames inside the
  interval) and ``outside_jump`` (level error on the two frames immediately
  outside the interval).  This keeps the two error sources of the prior study
  separate instead of collapsing them into one number.
* Histogram distance is the total-variation distance between 64-bin luma
  histograms, 0.5*sum|p-q| in [0,1] (a D-class illumination-consistency proxy).

All per-pixel work is done in float32/int16 so that the full 76-frame sequence
does not have to be promoted to float64 several times per condition.
"""
from __future__ import annotations

import math

import numpy as np

from .imaging import luma

C1 = (0.01 * 255.0) ** 2
C2 = (0.03 * 255.0) ** 2
HIST_BINS = 64


def _box_mean(a: np.ndarray, radius: int) -> np.ndarray:
    pad = np.pad(a, ((radius, radius), (radius, radius)), mode="reflect")
    ii = pad.cumsum(0).cumsum(1)
    k = 2 * radius + 1
    s = ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]
    return s / (k * k)


def ssim_luma(y1: np.ndarray, y2: np.ndarray, radius: int = 4) -> float:
    """Mean SSIM of two 2-D luma arrays (values 0..255, float32)."""
    mu1 = _box_mean(y1, radius)
    mu2 = _box_mean(y2, radius)
    mu1_sq, mu2_sq, mu1_mu2 = mu1 * mu1, mu2 * mu2, mu1 * mu2
    s11 = _box_mean(y1 * y1, radius) - mu1_sq
    s22 = _box_mean(y2 * y2, radius) - mu2_sq
    s12 = _box_mean(y1 * y2, radius) - mu1_mu2
    s11 = np.maximum(s11, 0.0)
    s22 = np.maximum(s22, 0.0)
    num = (2 * mu1_mu2 + C1) * (2 * s12 + C2)
    den = (mu1_sq + mu2_sq + C1) * (s11 + s22 + C2)
    return float(np.mean(num / den))


def psnr_rgb(out: np.ndarray, ref: np.ndarray, cap: float = 120.0) -> float:
    d = out.astype(np.int16) - ref.astype(np.int16)
    mse = float(np.mean(d.astype(np.float32) ** 2))
    if mse <= 1e-12:
        return cap
    return min(cap, 10.0 * math.log10(255.0 ** 2 / mse))


def luma_histogram(y: np.ndarray, bins: int = HIST_BINS) -> np.ndarray:
    v = np.clip(np.rint(y), 0, 255).astype(np.uint8)
    if bins == 256:
        h = np.bincount(v.ravel(), minlength=256)
    else:
        h = np.bincount((v.ravel() >> int(np.log2(256 // bins))), minlength=bins)
    p = h.astype(np.float64)
    s = p.sum()
    return p / s if s else p


def hist_tv_distance(h1: np.ndarray, h2: np.ndarray) -> float:
    return float(0.5 * np.abs(h1 - h2).sum())


def frame_metrics(out: np.ndarray, ref: np.ndarray, with_ssim: bool = False,
                  y_out: np.ndarray | None = None, y_ref: np.ndarray | None = None) -> dict:
    if y_out is None:
        y_out = luma(out.astype(np.float32))
    if y_ref is None:
        y_ref = luma(ref.astype(np.float32))
    d = out.astype(np.int16) - ref.astype(np.int16)
    m = {
        "y_mae": float(np.mean(np.abs(y_out - y_ref), dtype=np.float64)),
        "rgb_mae": float(np.mean(np.abs(d), dtype=np.float64)),
        "psnr": psnr_rgb(out, ref),
        "hist_dist": hist_tv_distance(luma_histogram(y_out), luma_histogram(y_ref)),
        "luma_out": float(np.mean(y_out, dtype=np.float64)),
        "luma_ref": float(np.mean(y_ref, dtype=np.float64)),
        "changed_pixels": int(np.any(d != 0, axis=-1).sum()),
    }
    if with_ssim:
        m["ssim"] = ssim_luma(y_out, y_ref)
    return m


def boundary_metrics(l_out: np.ndarray, l_ref: np.ndarray, start: int, length: int) -> dict:
    """Boundary jump error and its decomposition (all values in luma units)."""
    n = len(l_out)
    end = start + length
    left_jump_out = l_out[start] - l_out[start - 1] if start > 0 else 0.0
    left_jump_ref = l_ref[start] - l_ref[start - 1] if start > 0 else 0.0
    right_jump_out = l_out[end - 1] - l_out[end] if end < n else 0.0
    right_jump_ref = l_ref[end - 1] - l_ref[end] if end < n else 0.0
    left_err = abs(left_jump_out - left_jump_ref)
    right_err = abs(right_jump_out - right_jump_ref)
    estimator_bias = abs(l_out[start] - l_ref[start]) + abs(l_out[end - 1] - l_ref[end - 1])
    outside_jump = 0.0
    if start > 0:
        outside_jump += abs(l_out[start - 1] - l_ref[start - 1])
    if end < n:
        outside_jump += abs(l_out[end] - l_ref[end])
    return {
        "boundary_jump_error_sum": left_err + right_err,
        "boundary_left_error": left_err,
        "boundary_right_error": right_err,
        "boundary_estimator_bias": estimator_bias,
        "boundary_outside_jump": outside_jump,
    }


def temporal_metrics(l_out: np.ndarray, start: int, length: int, context: int = 2) -> dict:
    n = len(l_out)
    a = max(0, start - context)
    b = min(n, start + length + context)
    seg = l_out[a:b]
    d1 = np.diff(seg)
    if len(d1) == 0:
        return {"flicker_first_diff_var": 0.0, "flicker_second_diff_rms": 0.0}
    d2 = np.diff(d1)
    return {
        "flicker_first_diff_var": float(np.var(d1)),
        "flicker_second_diff_rms": float(np.sqrt(np.mean(d2 ** 2))) if len(d2) else 0.0,
    }


def sequence_metrics(out: np.ndarray, ref: np.ndarray, start: int, length: int,
                     l_out: np.ndarray, l_ref: np.ndarray) -> dict:
    """Region-preservation, boundary and flicker metrics for one condition."""
    n = out.shape[0]
    mask = np.zeros(n, dtype=bool)
    mask[start:start + length] = True
    changed = 0
    pix = 0
    rgb_sum = 0.0
    n_el = 0
    for t in np.nonzero(~mask)[0]:
        d = np.abs(out[t].astype(np.int16) - ref[t].astype(np.int16))
        changed += int(np.any(d != 0, axis=-1).sum())
        pix += d.shape[0] * d.shape[1]
        rgb_sum += float(d.sum(dtype=np.float64))
        n_el += d.size
    m = {
        "outside_changed_pixel_fraction": changed / pix if pix else 0.0,
        "outside_rgb_mae": rgb_sum / n_el if n_el else 0.0,
        "outside_y_mae": float(np.mean(np.abs(l_out - l_ref)[~mask], dtype=np.float64)) if (~mask).any() else 0.0,
    }
    m.update(boundary_metrics(l_out, l_ref, start, length))
    m.update(temporal_metrics(l_out, start, length))
    return m
