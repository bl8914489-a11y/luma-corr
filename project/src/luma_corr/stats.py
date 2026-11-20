"""Statistics: paired tests, effect sizes, cluster bootstrap.

Frames inside one video are not independent, so every comparison is reported
twice:

* frame-level Wilcoxon signed-rank test on all paired frames (high n, but
  pseudo-replicated);
* cluster-level test on the 15 per-video means (one pair per video), with a
  cluster bootstrap 95% interval (2000 resamples).

The cluster-level interval is the one quoted as the study's interval; the
frame-level p-value is reported only as a descriptive companion.
"""
from __future__ import annotations

import math

import numpy as np


def _rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=np.float64)
    ranks[order] = np.arange(1, len(x) + 1)
    # average ties
    sx = x[order]
    i = 0
    while i < len(sx):
        j = i
        while j + 1 < len(sx) and sx[j + 1] == sx[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = np.mean(np.arange(i + 1, j + 2))
        i = j + 1
    return ranks


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _exact_two_sided_p(ranks: np.ndarray, w_plus: float) -> float:
    """Exact sign-flip p-value for the signed-rank statistic.

    Under the null each pair contributes its rank with probability 1/2, so the
    distribution of W+ is a convolution of Bernoulli(1/2) rank contributions.
    The DP is exact for the observed |differences| (ties included through
    average ranks) and costs O(n * sum(ranks)) states.
    """
    mu = float(ranks.sum()) / 2.0
    dist = {0.0: 1.0}
    for r in ranks:
        nxt: dict[float, float] = {}
        for s, p in dist.items():
            nxt[s] = nxt.get(s, 0.0) + 0.5 * p
            nxt[s + r] = nxt.get(s + r, 0.0) + 0.5 * p
        dist = nxt
    return float(sum(p for s, p in dist.items() if abs(s - mu) >= abs(w_plus - mu) - 1e-9))


def wilcoxon_signed_rank(diff: np.ndarray) -> dict:
    d = np.asarray(diff, dtype=np.float64)
    d = d[~np.isnan(d)]
    d = d[d != 0.0]
    n = len(d)
    if n == 0:
        return {"n": 0, "w_plus": 0.0, "w_minus": 0.0, "z": float("nan"), "p": float("nan"),
                "rank_biserial": float("nan")}
    ranks = _rankdata(np.abs(d))
    w_plus = float(ranks[d > 0].sum())
    w_minus = float(ranks[d < 0].sum())
    mu = n * (n + 1) / 4.0
    # tie correction
    _, counts = np.unique(np.abs(d), return_counts=True)
    tie_term = float(np.sum(counts ** 3 - counts)) / 48.0
    var = n * (n + 1) * (2 * n + 1) / 24.0 - tie_term
    if var <= 0:
        z = 0.0
        p = 1.0
    else:
        z = (w_plus - mu) / math.sqrt(var)
        p = 2.0 * (1.0 - _phi(abs(z)))
    if n <= 25:
        p = _exact_two_sided_p(ranks, w_plus)
    r = (w_plus - w_minus) / max(w_plus + w_minus, 1e-12)
    return {"n": n, "w_plus": w_plus, "w_minus": w_minus, "z": float(z), "p": float(min(p, 1.0)),
            "rank_biserial": float(r), "exact": n <= 25}


def bootstrap_mean_ci(values: np.ndarray, n_boot: int = 2000, seed: int = 20261117) -> dict:
    v = np.asarray(values, dtype=np.float64)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n": 0}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    means = v[idx].mean(axis=1)
    return {"mean": float(v.mean()), "ci_low": float(np.percentile(means, 2.5)),
            "ci_high": float(np.percentile(means, 97.5)), "n": int(len(v))}


def cluster_bootstrap(diff_by_cluster: np.ndarray, n_boot: int = 2000, seed: int = 20261117) -> dict:
    """Percentile bootstrap over video clusters of the mean paired difference."""
    d = np.asarray(diff_by_cluster, dtype=np.float64)
    d = d[~np.isnan(d)]
    if len(d) == 0:
        return {"mean_diff": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
                "n_clusters": 0}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    return {"mean_diff": float(d.mean()), "median_diff": float(np.median(d)),
            "ci_low": float(np.percentile(means, 2.5)), "ci_high": float(np.percentile(means, 97.5)),
            "n_clusters": int(len(d))}


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    gt = sum(np.sum(a_i > b) for a_i in a)
    lt = sum(np.sum(a_i < b) for a_i in a)
    return float((gt - lt) / (len(a) * len(b)))


def holm(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = np.argsort(pvalues)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * pvalues[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj.tolist()
