"""Per-sequence RQ3 test-set error analysis at the selected CUSUM operating point."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import cusum_alarm, cusum_score, prune_segments  # noqa: E402
from luma_corr.detection_d1 import frame_metrics_from_mask, interval_metrics  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
CFG = json.load(open(os.path.join(WS, "project", "configs", "rq3_threshold_v1.json"), encoding="utf-8"))
OUT = os.path.join(WS, "results", "runs", "rq3_test_errors_v1")
FIELDS = ["sequence", "injection", "length", "recall", "precision", "f1", "iou",
          "fp_rate", "n_spans", "span0", "span1"]


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    rows = []
    for seq in CFG["split"]["test"]:
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for inj_id in ("A", "B", "B13"):
            if inj_id == "A":
                spec = InjectionSpec("A", "offset", 20.0, -1)
            elif inj_id == "B":
                spec = InjectionSpec("B", "gamma", gamma=2.0)
            else:
                spec = InjectionSpec("B13", "gamma", gamma=1.3)
            inj = apply_injection(ref, spec, 30, 12).injected
            score = cusum_score(inj)
            mask = prune_segments(cusum_alarm(score, k=0.5, h=8.0), min_len=2)
            fm = frame_metrics_from_mask(mask, 30, 12)
            im = interval_metrics([(int(a), int(b)) for a, b in _spans(mask)], 30, 12)
            rows.append({"sequence": seq, "injection": inj_id, "length": 12,
                         "recall": fm["recall"], "precision": fm["precision"], "f1": fm["f1"],
                         "iou": fm["iou"], "fp_rate": fm["fp_rate"],
                         "n_spans": len(_spans(mask)),
                         "span0": _spans(mask)[0][0] if _spans(mask) else "",
                         "span1": _spans(mask)[0][1] if _spans(mask) else ""})
            print(seq, inj_id, round(fm["recall"], 2), round(fm["precision"], 2), flush=True)
    with open(os.path.join(OUT, "per_condition.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    summary = {"run_id": "rq3_test_errors_v1", "k": 0.5, "h": 8.0, "length": 12,
               "test_sequences": CFG["split"]["test"],
               "mean_recall": float(np.mean([r["recall"] for r in rows])),
               "mean_precision": float(np.mean([r["precision"] for r in rows])),
               "finished_utc": datetime.now(timezone.utc).isoformat(),
               "environment": env_info()}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    write_json_atomic(os.path.join(OUT, "run_manifest.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def _spans(mask):
    idx = np.nonzero(mask)[0]
    if len(idx) == 0:
        return []
    spans, a = [], idx[0]
    for i in range(1, len(idx)):
        if idx[i] != idx[i - 1] + 1:
            spans.append((int(a), int(idx[i - 1]) + 1)); a = idx[i]
    spans.append((int(a), int(idx[-1]) + 1))
    return spans


if __name__ == "__main__":
    main()
