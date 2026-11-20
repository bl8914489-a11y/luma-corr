"""Frame I/O and colour helpers.

All images are kept as uint8 RGB arrays shaped (N, H, W, 3).  Luma is the
ITU-R BT.601 definition used by YCbCr video pipelines:

    Y = 0.299 R + 0.587 G + 0.114 B

No colour conversion is applied to the stored frames themselves; metrics
compute luma from the RGB arrays.
"""
from __future__ import annotations

import hashlib
import os

import numpy as np
from PIL import Image

Y_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float64)


def luma(rgb: np.ndarray) -> np.ndarray:
    """BT.601 luma of an RGB array; trailing axis must be 3."""
    return rgb[..., 0] * Y_WEIGHTS[0] + rgb[..., 1] * Y_WEIGHTS[1] + rgb[..., 2] * Y_WEIGHTS[2]


def frame_luma_means(rgb: np.ndarray) -> np.ndarray:
    """Per-frame spatial mean luma, shape (N,).

    Uses integer channel sums (luma is linear in the channels), which is both
    exact and much faster than materialising the full luma volume.
    """
    sums = rgb.sum(axis=(1, 2), dtype=np.uint64)
    h, w = rgb.shape[1], rgb.shape[2]
    return (sums[:, 0] * Y_WEIGHTS[0] + sums[:, 1] * Y_WEIGHTS[1] +
            sums[:, 2] * Y_WEIGHTS[2]) / float(h * w)


def load_frames(directory: str, pattern: str = ".jpg") -> np.ndarray:
    files = sorted(f for f in os.listdir(directory) if f.lower().endswith(pattern))
    if not files:
        raise FileNotFoundError(f"no {pattern} frames in {directory}")
    frames = []
    for i, f in enumerate(files):
        idx = int(f.split(".")[0])
        if idx != i:
            raise ValueError(f"non-contiguous frame index {f} at position {i} in {directory}")
        with Image.open(os.path.join(directory, f)) as im:
            frames.append(np.asarray(im.convert("RGB"), dtype=np.uint8))
    arr = np.stack(frames)
    if arr.ndim != 4 or arr.shape[-1] != 3:
        raise ValueError(f"unexpected frame shape {arr.shape}")
    return arr


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_array_uint8(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.uint8).tobytes()).hexdigest()


def to_uint8(x: np.ndarray) -> np.ndarray:
    """Clip and round a float array to uint8 (numpy rounds half to even)."""
    return np.clip(np.rint(x), 0.0, 255.0).astype(np.uint8)


def scale_rgb_by_luma(rgb: np.ndarray, y_old: np.ndarray, y_new: np.ndarray) -> np.ndarray:
    """Scale RGB channels so that their BT.601 luma becomes ``y_new``.

    Chromaticity is preserved: every channel is multiplied by
    ``y_new / y_old`` (where ``y_old`` is non-zero).
    """
    out = rgb.astype(np.float64, copy=True)
    ratio = np.ones_like(y_old)
    nz = y_old > 1e-6
    ratio[nz] = y_new[nz] / y_old[nz]
    out *= ratio[..., None]
    return out
