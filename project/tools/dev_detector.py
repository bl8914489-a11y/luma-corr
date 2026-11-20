"""Development harness for the RQ3 detector (not part of a reported run).

Compares score constructions and alarm rules on the injected intervals so that
the final detector configuration can be fixed before the reported run.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import hist_scores  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402

ROOT = r"F:\周四焜哥论文"
START = 30
SEQS = sorted(os.listdir(os.path.join(ROOT, "data", "frames")))
INJS = [("A", InjectionSpec("A", "offset", 20.0, -1)), ("B", InjectionSpec("B", "gamma", gamma=2.0)),
        ("B13", InjectionSpec("B13", "gamma", gamma=1.3))]


def smooth(x, w):
    if w <= 1:
        return x.copy()
    r = w // 2
    return np.array([np.mean(x[max(0, t - r):min(len(x), t + r + 1)]) for t in range(len(x))])


def robust_z(x):
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return (x - med) / max(1.4826 * mad, 1e-6), med, mad


def cusum(z, k, h):
    mask = np.zeros(len(z), bool)
    c = 0.0
    for t in range(len(z)):
        c = max(0.0, c + z[t] - k)
        if c > h:
            mask[t] = True
            c = h * 0.5
    return mask


def hyst(z, hi, lo, enter=2, exit=3):
    mask = np.zeros(len(z), bool)
    active = False
    rh = rl = 0
    for t in range(len(z)):
        if not active:
            rh = rh + 1 if z[t] >= hi else 0
            if rh >= enter:
                active = True
                mask[t - enter + 1:t + 1] = True
                rl = 0
        else:
            rl = rl + 1 if z[t] <= lo else 0
            if rl >= exit:
                active = False
                rh = 0
            else:
                mask[t] = True
    return mask


def prf(mask, start, length):
    lab = np.zeros(len(mask), bool)
    lab[start:start + length] = True
    tp = int((mask & lab).sum()); fp = int((mask & ~lab).sum()); fn = int((~mask & lab).sum())
    r = tp / max(tp + fn, 1); p = tp / max(tp + fp, 1)
    return r, p, tp / max(tp + fp + fn, 1)


def main():
    data = {}
    for seq in SEQS:
        ref = load_frames(os.path.join(ROOT, "data", "frames", seq))
        l = frame_luma_means(ref)
        zl = np.abs(l - np.median(l)) / max(1.4826 * np.median(np.abs(l - np.median(l))), 1e-6)
        _, js_clean = hist_scores(ref)
        data[(seq, "CLEAN")] = (js_clean, zl)
        for name, spec in INJS:
            for length in (1, 4, 12):
                inj = apply_injection(ref, spec, START, length).injected
                _, js = hist_scores(inj)
                lj = frame_luma_means(inj)
                zlj = np.abs(lj - np.median(lj)) / max(1.4826 * np.median(np.abs(lj - np.median(lj))), 1e-6)
                data[(seq, name, length)] = (js, zlj)

    def run(tag, build, rule, lengths=(1, 4, 12)):
        acc = {}
        for length in lengths:
            vals = []
            for seq in SEQS:
                for name, _ in INJS:
                    js, zlj = data[(seq, name, length)]
                    z = build(js, zlj)
                    mask = rule(z)
                    r, p, iou = prf(mask, START, length)
                    f1 = 2 * p * r / max(p + r, 1e-12)
                    vals.append((r, p, iou, f1))
            vals = np.array(vals)
            acc[length] = (vals[:, 0].mean(), vals[:, 1].mean(), vals[:, 2].mean(), vals[:, 3].mean())
        fp = []
        for seq in SEQS:
            js, zl = data[(seq, "CLEAN")]
            z = build(js, zl)
            fp.append(rule(z).mean())
        print(tag, {k: tuple(round(x, 3) for x in v) for k, v in acc.items()}, "FP=%.3f" % np.mean(fp))

    for sm in (1, 3):
        for zt in (2.0, 2.5, 3.0):
            run(f"js_z{zt}_s{sm}_hyst", lambda js, zl, sm=sm: smooth(robust_z(js)[0], sm),
                lambda z, zt=zt: hyst(z, zt, 0.5 * zt))
    for sm in (1, 3):
        for k, h in ((0.25, 3.0), (0.5, 4.0), (0.5, 6.0)):
            run(f"comb_cusum_k{k}_h{h}_s{sm}",
                lambda js, zl, sm=sm: smooth(np.maximum(robust_z(js)[0], zl), sm),
                lambda z, k=k, h=h: cusum(z, k, h))
    for sm in (1, 3):
        for zt in (2.0, 2.5, 3.0):
            run(f"comb_z{zt}_s{sm}_hyst",
                lambda js, zl, sm=sm: smooth(np.maximum(robust_z(js)[0], zl), sm),
                lambda z, zt=zt: hyst(z, zt, 0.5 * zt))


if __name__ == "__main__":
    main()
