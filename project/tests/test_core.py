import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.imaging import frame_luma_means, luma, to_uint8  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import (boundary_metrics, hist_tv_distance, luma_histogram,  # noqa: E402
                               psnr_rgb, sequence_metrics, ssim_luma)
from luma_corr.provenance import config_sha256, canonical_json  # noqa: E402
from luma_corr.stats import bootstrap_mean_ci, cluster_bootstrap, wilcoxon_signed_rank  # noqa: E402


def make_frames(n=12, h=12, w=12, value=100):
    return np.full((n, h, w, 3), value, dtype=np.uint8)


def gradient_frames(n=12, h=32, w=32):
    x = np.linspace(0, 255, w, dtype=np.float64)
    y = np.linspace(0, 255, h, dtype=np.float64)
    g = np.sqrt(x[None, :] * y[:, None])
    base = np.stack([g, g, g], axis=-1)
    return np.stack([np.clip(np.rint(base), 0, 255).astype(np.uint8) for _ in range(n)])


class TestInjection(unittest.TestCase):
    def test_offset_only_inside_interval(self):
        frames = make_frames()
        res = apply_injection(frames, InjectionSpec("A", "offset", 20.0, -1), 4, 2)
        self.assertTrue(np.array_equal(res.injected[:4], frames[:4]))
        self.assertTrue(np.array_equal(res.injected[6:], frames[6:]))
        self.assertEqual(int(res.injected[4, 0, 0, 0]), 80)

    def test_offset_clip_fraction_measured_before_clamp(self):
        frames = make_frames(value=10)
        res = apply_injection(frames, InjectionSpec("A", "offset", 20.0, -1), 4, 2)
        self.assertAlmostEqual(res.clip_fraction, 1.0)
        self.assertEqual(int(res.injected[4, 0, 0, 0]), 0)

    def test_gamma_injection_has_no_injection_clipping(self):
        res = apply_injection(gradient_frames(), InjectionSpec("B", "gamma", gamma=2.0), 4, 2)
        self.assertEqual(res.clip_fraction, 0.0)

    def test_invalid_interval_rejected(self):
        with self.assertRaises(ValueError):
            apply_injection(make_frames(), InjectionSpec("A", "offset", 20.0, -1), 10, 5)


class TestImaging(unittest.TestCase):
    def test_luma_linearity(self):
        a = np.array([[[10, 20, 30]]], dtype=np.uint8)
        self.assertAlmostEqual(float(luma(a.astype(np.float64))[0, 0]), 0.299 * 10 + 0.587 * 20 + 0.114 * 30)

    def test_frame_luma_means_matches_full_computation(self):
        frames = gradient_frames()
        fast = frame_luma_means(frames)
        slow = luma(frames.astype(np.float64)).mean(axis=(1, 2))
        self.assertTrue(np.allclose(fast, slow, atol=1e-9))

    def test_to_uint8_rounds_and_clips(self):
        x = np.array([-1.0, 0.4, 255.6, 300.0])
        self.assertEqual(to_uint8(x).tolist(), [0, 0, 255, 255])


class TestMetrics(unittest.TestCase):
    def test_identity_metrics(self):
        f = gradient_frames()
        self.assertEqual(psnr_rgb(f[0], f[0]), 120.0)
        self.assertAlmostEqual(ssim_luma(luma(f[0].astype(np.float32)), luma(f[0].astype(np.float32))), 1.0)
        self.assertEqual(hist_tv_distance(luma_histogram(luma(f[0].astype(np.float32))),
                                          luma_histogram(luma(f[0].astype(np.float32)))), 0.0)

    def test_histogram_distance_bounded(self):
        h1 = luma_histogram(np.zeros((8, 8)))
        h2 = luma_histogram(np.full((8, 8), 255.0))
        self.assertAlmostEqual(hist_tv_distance(h1, h2), 1.0)

    def test_boundary_decomposition(self):
        l_ref = np.full(20, 100.0)
        l_out = l_ref.copy()
        l_out[8] += 10
        l_out[9] += 10
        m = boundary_metrics(l_out, l_ref, 8, 2)
        self.assertAlmostEqual(m["boundary_left_error"], 10.0)
        self.assertAlmostEqual(m["boundary_right_error"], 10.0)
        self.assertAlmostEqual(m["boundary_estimator_bias"], 20.0)
        self.assertAlmostEqual(m["boundary_outside_jump"], 0.0)

    def test_sequence_metrics_local_has_zero_outside_change(self):
        ref = gradient_frames()
        out = ref.copy()
        out[4] = np.clip(out[4].astype(int) + 20, 0, 255).astype(np.uint8)
        l_ref = frame_luma_means(ref)
        l_out = frame_luma_means(out)
        m = sequence_metrics(out, ref, 4, 1, l_out, l_ref)
        self.assertEqual(m["outside_changed_pixel_fraction"], 0.0)
        self.assertGreater(m["boundary_estimator_bias"], 0.0)


class TestCorrections(unittest.TestCase):
    def test_noop_returns_input(self):
        frames = gradient_frames()
        res = correct({"id": "A1", "kind": "noop"}, frames, 4, 2)
        self.assertTrue(np.array_equal(res.out, frames))

    def test_local_scope_preserves_outside_frames(self):
        ref = gradient_frames()
        inj = apply_injection(ref, InjectionSpec("A", "offset", 20.0, -1), 4, 2).injected
        for kind in ({"id": "A2", "kind": "offset_median", "window": 7},
                     {"id": "A3", "kind": "offset_linear", "k": 3}):
            out = correct(kind, inj, 4, 2).out
            self.assertTrue(np.array_equal(out[:4], inj[:4]))
            self.assertTrue(np.array_equal(out[6:], inj[6:]))

    def test_linear_offset_recovers_constant_offset(self):
        ref = make_frames(value=100)
        inj = apply_injection(ref, InjectionSpec("A", "offset", 20.0, -1), 4, 2).injected
        out = correct({"id": "A3", "kind": "offset_linear", "k": 3}, inj, 4, 2).out
        self.assertTrue(np.array_equal(out, ref))

    def test_soft_knee_reduces_hard_clipping(self):
        ref = gradient_frames()
        inj = apply_injection(ref, InjectionSpec("B", "gamma", gamma=2.0), 4, 2).injected
        hard = correct({"id": "h", "kind": "offset_linear", "k": 3, "soft_knee": 0.0}, inj, 4, 2)
        soft = correct({"id": "s", "kind": "offset_linear", "k": 3, "soft_knee": 235.0}, inj, 4, 2)
        self.assertGreater(hard.info["clip_fraction"], soft.info["clip_fraction"])

    def test_global_scope_may_touch_outside(self):
        ref = gradient_frames()
        frames = np.stack([np.clip(ref[t].astype(int) + 4 * t, 0, 255).astype(np.uint8)
                           for t in range(ref.shape[0])])
        inj = apply_injection(frames, InjectionSpec("A", "offset", 60.0, -1), 4, 2).injected
        out = correct({"id": "A4", "kind": "offset_median", "window": 7, "scope": "global"}, inj, 4, 2).out
        self.assertFalse(np.array_equal(out[:4], inj[:4]))


class TestStats(unittest.TestCase):
    def test_wilcoxon_all_positive(self):
        r = wilcoxon_signed_rank(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        self.assertEqual(r["w_plus"], 15.0)
        self.assertAlmostEqual(r["rank_biserial"], 1.0)
        self.assertLess(r["p"], 0.1)

    def test_wilcoxon_zero_differences(self):
        r = wilcoxon_signed_rank(np.zeros(5))
        self.assertEqual(r["n"], 0)

    def test_bootstrap_contains_mean(self):
        ci = bootstrap_mean_ci(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        self.assertLessEqual(ci["ci_low"], ci["mean"])
        self.assertGreaterEqual(ci["ci_high"], ci["mean"])

    def test_cluster_bootstrap_deterministic(self):
        d = np.array([1.0, -1.0, 2.0, 0.0])
        a = cluster_bootstrap(d)
        b = cluster_bootstrap(d)
        self.assertEqual(a["ci_low"], b["ci_low"])


class TestProvenance(unittest.TestCase):
    def test_config_hash_order_independent(self):
        a = {"x": 1, "y": [1, 2]}
        b = {"y": [1, 2], "x": 1}
        self.assertEqual(config_sha256(a), config_sha256(b))
        self.assertIn('"x":1', canonical_json(a))

    def test_config_hash_changes(self):
        self.assertNotEqual(config_sha256({"x": 1}), config_sha256({"x": 2}))


class TestDetection(unittest.TestCase):
    def setUp(self):
        self.n = 30
        yy, xx = np.mgrid[0:16, 0:16]
        base = 120 + (xx + yy) % 3
        self.frames = np.stack([np.clip(np.stack([base + (t % 2)] * 3, axis=-1), 0, 255).astype(np.uint8)
                                for t in range(self.n)])

    def test_median_dev_detects_single_frame(self):
        from luma_corr.detection import detect
        inj = self.frames.copy()
        inj[10] = np.clip(inj[10].astype(int) - 40, 0, 255).astype(np.uint8)
        res = detect(inj, {"id": "m", "kind": "median_dev", "window": 7, "threshold": 1.0})
        self.assertTrue(res["mask"][10])

    def test_hist_cusum_detects_persistent_step(self):
        from luma_corr.detection import detect
        inj = self.frames.copy()
        inj[10:22] = np.clip(inj[10:22].astype(int) - 40, 0, 255).astype(np.uint8)
        res = detect(inj, {"id": "k", "kind": "hist_kl_cusum", "window": 41, "smooth": 3,
                           "k": 0.5, "h": 6.0, "min_len": 2})
        self.assertGreaterEqual(int(res["mask"][10:22].sum()), 8)

    def test_hist_cusum_quiet_on_clean(self):
        from luma_corr.detection import detect
        res = detect(self.frames, {"id": "k", "kind": "hist_kl_cusum", "window": 41, "smooth": 3,
                                   "k": 0.5, "h": 6.0, "min_len": 2})
        self.assertEqual(int(res["mask"].sum()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
