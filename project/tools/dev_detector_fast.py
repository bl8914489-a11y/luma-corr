"""Fast cached sweep for the RQ3 detector design (development only)."""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.imaging import frame_luma_means, load_frames, luma  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import luma_histogram  # noqa: E402

ROOT = r"F:\周四焜哥论文"
START = 30
SEQS = sorted(os.listdir(os.path.join(ROOT, "data", "frames")))
INJS = [("A", InjectionSpec("A", "offset", 20.0, -1)), ("B", InjectionSpec("B", "gamma", gamma=2.0)),
        ("B13", InjectionSpec("B13", "gamma", gamma=1.3))]
LENGTHS = (1, 4, 12)


def smooth(x, w):
    if w <= 1:
        return x.copy()
    r = w // 2
    c = np.cumsum(np.r_[0.0, x])
    out = np.empty(len(x))
    for t in range(len(x)):
        a, b = max(0, t - r), min(len(x), t + r + 1)
        out[t] = (c[b] - c[a]) / (b - a)
    return out


def rz(x):
    m = np.median(x)
    mad = np.median(np.abs(x - m))
    return (x - m) / max(1.4826 * mad, 1e-6)


def rolling_median_hist(H, win):
    n = len(H)
    r = win // 2
    B = np.empty_like(H)
    for t in range(n):
        B[t] = np.median(H[max(0, t - r):min(n, t + r + 1)], axis=0)
    B = np.clip(B, 1e-9, None)
    B /= B.sum(axis=1, keepdims=True)
    return B


def js_scores(H, B):
    h = np.clip(H, 1e-9, None)
    h /= h.sum(axis=1, keepdims=True)
    m = 0.5 * (h + B)
    return 0.5 * np.sum(h * np.log(h / m), axis=1) + 0.5 * np.sum(B * np.log(B / m), axis=1)


def cusum(z, k, h):
    mask = np.zeros(len(z), bool)
    c = 0.0
    for t in range(len(z)):
        c = max(0.0, c + z[t] - k)
        if c > h:
            mask[t] = True
            c = 0.5 * h
    return mask


def prune(mask, minlen):
    out = mask.copy()
    i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            if j - i < minlen:
                out[i:j] = False
            i = j
        else:
            i += 1
    return out


def prf(mask, length):
    lab = np.zeros(len(mask), bool)
    lab[START:START + length] = True
    tp = int((mask & lab).sum()); fp = int((mask & ~lab).sum()); fn = int((~mask & lab).sum())
    r = tp / max(tp + fn, 1); p = tp / max(tp + fp, 1)
    return r, p, tp / max(tp + fp + fn, 1)


def main():
    cache = {}
    for seq in SEQS:
        ref = load_frames(os.path.join(ROOT, "data", "frames", seq))
        cache[(seq, "CLEAN")] = (ref, np.stack([luma_histogram(luma(f.astype(np.float32))) for f in ref]))
        for name, spec in INJS:
            for L in LENGTHS:
                fr = apply_injection(ref, spec, START, L).injected
                H = np.stack([luma_histogram(luma(f.astype(np.float32))) for f in fr])
                cache[(seq, name, L)] = (fr, H)
    print("cache ready", len(cache), flush=True)

    for win in (31, 41):
        for k, h in ((0.5, 4.0), (0.5, 6.0), (0.25, 3.0)):
            for minlen in (1, 2):
                res = {L: [] for L in LENGTHS}
                fp = []
                for seq in SEQS:
                    ref, Hc = cache[(seq, "CLEAN")]
                    l = frame_luma_means(ref)
                    bc = rolling_median_hist(Hc, win)
                    zc = np.maximum(rz(js_scores(Hc, bc)), rz(np.abs(l - np.median(l))))
                    fp.append(prune(cusum(smooth(zc, 3), k, h), minlen).mean())
                    for name, _ in INJS:
                        for L in LENGTHS:
                            fr, H = cache[(seq, name, L)]
                            ll = frame_luma_means(fr)
                            B = rolling_median_hist(H, win)
                            z = np.maximum(rz(js_scores(H, B)), rz(np.abs(ll - np.median(ll))))
                            mask = prune(cusum(smooth(z, 3), k, h), minlen)
                            res[L].append(prf(mask, L))
                summ = {L: tuple(round(float(np.mean([x[i] for x in v])), 3) for i in range(3)) for L, v in res.items()}
                print(f"win={win} k={k} h={h} minlen={minlen} FP={np.mean(fp):.3f} {summ}", flush=True)


if __name__ == "__main__":
    main()
