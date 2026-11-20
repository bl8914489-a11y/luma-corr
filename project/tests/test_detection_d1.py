import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection_d1 import (d1_score, d2_spans, eq5_mask, frame_metrics_from_mask,  # noqa: E402
                                    hist_stack, interval_metrics, js_rows, kl_rows, smooth_time)


class TestD1Score(unittest.TestCase):
    def test_hist_stack_normalised(self):
        frames = np.random.default_rng(0).integers(0, 256, size=(6, 8, 8, 3), dtype=np.uint8)
        H = hist_stack(frames, 64)
        self.assertEqual(H.shape, (6, 64))
        self.assertTrue(np.allclose(H.sum(axis=1), 1.0))

    def test_smooth_time_preserves_mass(self):
        H = np.full((5, 8), 1.0 / 8.0)
        S = smooth_time(H, 1.5)
        self.assertTrue(np.allclose(S.sum(axis=1), 1.0, atol=1e-9))
        self.assertTrue(np.all(S >= 0))

    def test_kl_nonnegative_and_js_symmetric(self):
        p = np.array([[0.7, 0.2, 0.1], [0.1, 0.1, 0.8]])
        q = np.array([[0.6, 0.3, 0.1], [0.2, 0.2, 0.6]])
        self.assertTrue(np.all(kl_rows(p, q) >= -1e-12))
        self.assertTrue(np.allclose(js_rows(p, q), js_rows(q, p)))

    def test_d1_score_changes_with_shift(self):
        H = np.full((10, 32), 1.0 / 32.0)
        H[4:6] = 0.0
        H[4:6, 20:] = 1.0 / 12.0
        s = d1_score(H, sigma=1.0, mode="js")
        self.assertGreater(float(s[5]), float(s[0]))


class TestEq5(unittest.TestCase):
    def test_eq5_flags_spike(self):
        s = np.full(20, 0.01)
        s[10] = 1.0
        mask = eq5_mask(s, neighbors=3, alpha=1.0)
        self.assertTrue(mask[10])
        self.assertGreater(int(mask.sum()), 0)


class TestD2(unittest.TestCase):
    def test_plateau_span(self):
        s = np.zeros(40)
        s[10:22] = 5.0
        spans = d2_spans(s, hi=3.0, lo=1.5, min_len=2, max_gap=2, expand=True, refine=False)
        self.assertEqual(spans, [(10, 22)])

    def test_gap_merge(self):
        s = np.zeros(30)
        s[5:8] = 5.0
        s[10:13] = 5.0
        spans = d2_spans(s, hi=3.0, lo=1.5, min_len=1, max_gap=2, expand=False, refine=False)
        self.assertEqual(spans, [(5, 13)])

    def test_min_length_drops_short(self):
        s = np.zeros(30)
        s[5] = 5.0
        spans = d2_spans(s, hi=3.0, lo=1.5, min_len=2, max_gap=2, expand=False, refine=False)
        self.assertEqual(spans, [])

    def test_refine_snaps_to_luma_step(self):
        s = np.zeros(40)
        s[10:22] = 5.0
        luma = np.full(40, 100.0)
        luma[10:] = 80.0
        spans = d2_spans(s, hi=3.0, lo=1.5, luma_means=luma, min_len=2, max_gap=2,
                         expand=True, refine=True)
        self.assertEqual(spans[0][0], 10)


class TestIntervalMetrics(unittest.TestCase):
    def test_best_iou(self):
        m = interval_metrics([(28, 44), (60, 64)], start=30, length=12)
        self.assertAlmostEqual(m["interval_iou"], 12 / 16)
        self.assertEqual(m["interval_hit"], 1.0)
        self.assertEqual(m["span_start"], 28)

    def test_empty(self):
        m = interval_metrics([], start=30, length=12)
        self.assertTrue(np.isnan(m["interval_iou"]))

    def test_frame_metrics(self):
        mask = np.zeros(76, dtype=bool)
        mask[30:40] = True
        m = frame_metrics_from_mask(mask, 30, 12)
        self.assertEqual(m["tp"], 10)
        self.assertEqual(m["fn"], 2)
        self.assertEqual(m["fp"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
