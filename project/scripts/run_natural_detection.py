"""Run CUSUM on the 100 natural clips and compare with the returned labels (preliminary)."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import cusum_alarm, cusum_score, prune_segments  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.provenance import env_info, write_json_atomic  # noqa: E402

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "results", "runs", os.environ.get("NAT_RUN", "natural_detection_v1"))
LABELS = os.environ.get("NAT_LABELS", os.path.join(WS, "标注", "回收", "标注_标准化_2026-11-19.csv"))
FIELDS = ["clip_id", "sequence", "clip_start", "has_defect", "start", "end", "type",
          "pred_any", "pred_frames", "recall_0", "precision_0", "recall_1", "precision_1"]
LAB = list(csv.DictReader(open(LABELS, encoding="utf-8")))
IDX = {r["clip_id"]: r for r in csv.DictReader(open(os.path.join(WS, "标注", "clip_index.csv"), encoding="utf-8"))}


def main():
    if os.path.exists(OUT):
        raise SystemExit("exists")
    os.makedirs(OUT)
    rows = []
    for r in LAB:
        if r["has_defect"] not in ("0", "1"):
            continue
        cid = r["clip_id"]; seq = r["sequence"]; st = int(r["clip_start"])
        ref = load_frames(os.path.join(WS, "data", "frames", seq))[st:st + 24]
        mask = prune_segments(cusum_alarm(cusum_score(ref), k=0.5, h=8.0), min_len=2)
        pred = mask.astype(int)
        rec0 = pre0 = rec1 = pre1 = 0.0
        if r["has_defect"] == "1" and r["start"] != "" and r["end"] != "":
            s, e = int(r["start"]), int(r["end"])
            for tag, (a, b) in (("0", (max(0, s), min(24, e + 1))), ("1", (max(0, s - 1), min(24, e)))):
                gt = np.zeros(24, int); gt[a:b] = 1
                tp = int((pred & gt).sum()); fp = int((pred & (1 - gt)).sum()); fn = int(((1 - pred) & gt).sum())
                if tag == "0": rec0, pre0 = tp / max(tp + fn, 1), tp / max(tp + fp, 1)
                else: rec1, pre1 = tp / max(tp + fn, 1), tp / max(tp + fp, 1)
        rows.append({"clip_id": cid, "sequence": seq, "clip_start": st, "has_defect": int(r["has_defect"]),
                     "start": r["start"], "end": r["end"], "type": r["type"],
                     "pred_any": int(mask.any()), "pred_frames": int(mask.sum()),
                     "recall_0": rec0, "precision_0": pre0, "recall_1": rec1, "precision_1": pre1})
    with open(os.path.join(OUT, "per_clip.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    y = np.array([r["has_defect"] for r in rows]); p = np.array([r["pred_any"] for r in rows])
    tp = int(((y == 1) & (p == 1)).sum()); fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum()); tn = int(((y == 0) & (p == 0)).sum())
    pos = [r for r in rows if r["has_defect"] == 1]
    summary = {"run_id": os.environ.get("NAT_RUN", "natural_detection_v1"), "n": len(rows), "n_positive": int(y.sum()),
               "clip_confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
               "clip_precision": tp / max(tp + fp, 1), "clip_recall": tp / max(tp + fn, 1),
               "clip_accuracy": (tp + tn) / max(len(rows), 1),
               "interval_mean_recall_0": float(np.mean([r["recall_0"] for r in pos])),
               "interval_mean_precision_0": float(np.mean([r["precision_0"] for r in pos])),
               "interval_mean_recall_1": float(np.mean([r["recall_1"] for r in pos])),
               "interval_mean_precision_1": float(np.mean([r["precision_1"] for r in pos])),
               "by_type": {}, "environment": env_info(),
               "finished_utc": datetime.now(timezone.utc).isoformat()}
    for typ in sorted({r["type"] for r in pos}):
        rs = [r for r in pos if r["type"] == typ]
        summary["by_type"][typ] = {"n": len(rs),
                                   "clip_recall": float(np.mean([r["pred_any"] for r in rs])),
                                   "interval_recall_0": float(np.mean([r["recall_0"] for r in rs])),
                                   "interval_recall_1": float(np.mean([r["recall_1"] for r in rs]))}
    write_json_atomic(os.path.join(OUT, "summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
