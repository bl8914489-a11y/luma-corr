"""Controlled synthetic defect injection.

Two families, both applied only to the zero-based half-open interval
``[start, start + length)`` of an otherwise untouched sequence:

* ``offset``  I' = clip(I + direction * amount, 0, 255)   (experiment A)
* ``gamma``   I' = 255 * (I / 255) ** gamma              (experiment B / B')

Injection is deterministic and its clipping is measured *before* clamping, so
"injection clipping" and "correction clipping" can never be conflated.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .imaging import sha256_array_uint8


@dataclass(frozen=True)
class InjectionSpec:
    id: str
    kind: str          # "offset" | "gamma"
    amount: float = 0.0
    direction: int = -1
    gamma: float = 1.0
    channels: str = "RGB"

    def as_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "amount": self.amount,
                "direction": self.direction, "gamma": self.gamma, "channels": self.channels}

    @classmethod
    def from_dict(cls, d: dict) -> "InjectionSpec":
        return cls(id=str(d["id"]), kind=str(d["kind"]), amount=float(d.get("amount", 0.0)),
                   direction=int(d.get("direction", -1)), gamma=float(d.get("gamma", 1.0)),
                   channels=str(d.get("channels", "RGB")))


@dataclass
class InjectionResult:
    injected: np.ndarray
    spec: InjectionSpec
    start: int
    length: int
    clipped_channels: int
    total_channels: int
    clip_fraction: float
    magnitude_mean_abs_diff: float
    per_frame_sha256: dict = field(default_factory=dict)


def apply_injection(frames: np.ndarray, spec: InjectionSpec, start: int, length: int) -> InjectionResult:
    if frames.dtype != np.uint8:
        raise TypeError("injection expects uint8 frames")
    n = frames.shape[0]
    end = start + length
    if not (0 <= start < end <= n):
        raise ValueError(f"invalid interval [{start},{end}) for {n} frames")

    out = frames.copy()
    block = frames[start:end].astype(np.float64)

    if spec.kind == "offset":
        shifted = block + spec.direction * spec.amount
    elif spec.kind == "gamma":
        if spec.gamma <= 0:
            raise ValueError("gamma must be > 0")
        shifted = 255.0 * np.power(np.clip(block, 0.0, 255.0) / 255.0, spec.gamma)
    else:
        raise ValueError(f"unknown injection kind {spec.kind!r}")

    clipped = int(np.sum((shifted < 0.0) | (shifted > 255.0)))
    total = int(shifted.size)
    out[start:end] = np.clip(np.rint(shifted), 0.0, 255.0)
    magnitude = float(np.abs(out[start:end].astype(np.float64) - block).mean())
    sha = {t: sha256_array_uint8(out[t]) for t in range(start, end)}
    return InjectionResult(
        injected=out, spec=spec, start=start, length=length,
        clipped_channels=clipped, total_channels=total,
        clip_fraction=clipped / max(total, 1),
        magnitude_mean_abs_diff=magnitude,
        per_frame_sha256=sha,
    )


def interval_mask(n: int, start: int, length: int) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    m[start:start + length] = True
    return m
