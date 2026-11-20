"""Pre-registered CUSUM threshold selection on a validation split.

Validation: paint, sailboat, book, retriever (sha256 order, fixed before any
selection).  Test: the other 9 sequences.  The script selects (k, h) and whether
to union with the global-histogram detector using validation only, then reports
test at the selected point and at the a-priori h=6 point.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.detection import (cusum_alarm, cusum_score, detect, dual_baseline_score,  # noqa: E402
                                 prune_segments)
from luma_corr.detection_d1 import (frame_metrics_from_mask, interval_metrics,  # noqa: E402
                                    spans_from_mask)
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.provenance import (code_tree_sha256, config_sha256, env_info, sha256_file,  # noqa: E402
                                  write_json_atomic)

FIELDS = ["split", "k", "h", "variant", "length", "injection", "n", "recall", "precision",
          "f1", "iou", "interval_iou"]


def evals(mask, spans, start, length):
    fm = frame_metrics_from_mask(mask, start, length)
    im = interval_metrics(spans, start, length)
    return fm, im


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--workspace", default=r"F:\周四焜哥论文")
    ap.add_argument("--run-id", default="rq3_threshold_v1")
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    with open(os.path.join(args.workspace, "data", "manifest", "dataset_manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    all_seqs = sorted(manifest["sequences"])
    val, test = cfg["split"]["validation"], cfg["split"]["test"]
    assert set(val) | set(test) == set(all_seqs) and not (set(val) & set(test))
    start = int(cfg["start"])
    lengths = cfg["lengths"]
    score_kind = cfg.get("score", "cusum")
    score_fn = dual_baseline_score if score_kind == "dual" else cusum_score
    root = os.path.join(args.workspace, "results", "runs")
    final = os.path.join(root, args.run_id)
    staging = os.path.join(root, f".staging_{args.run_id}")
    if os.path.exists(final):
        raise SystemExit(f"existing {final}")
    os.makedirs(staging, exist_ok=True)
    t0 = time.time()
    write_json_atomic(os.path.join(staging, "run_manifest.json"), {
        "run_id": args.run_id, "kind": "rq3_threshold_selection", "score_kind": score_kind, "config": cfg,
        "config_sha256": config_sha256(cfg),
        "code_tree_sha256": code_tree_sha256([os.path.join(args.workspace, "project", "src")]),
        "environment": env_info(), "command": " ".join(sys.argv),
        "started_utc": datetime.now(timezone.utc).isoformat(),
    })

    # cache scores and masks
    cache = {}
    for seq in all_seqs:
        ref = load_frames(os.path.join(args.workspace, "data", "frames", seq))
        for inj_id in cfg["injections"]:
            spec = InjectionSpec.from_dict(next(d for d in [
                {"id": "A", "kind": "offset", "amount": 20.0, "direction": -1, "gamma": 1.0},
                {"id": "B", "kind": "gamma", "amount": 0.0, "direction": -1, "gamma": 2.0},
                {"id": "B13", "kind": "gamma", "amount": 0.0, "direction": -1, "gamma": 1.3},
            ] if d["id"] == inj_id))
            for L in lengths:
                frames = apply_injection(ref, spec, start, L).injected
                score = score_fn(frames, 64, 41, int(cfg["grid"]["smooth"]))
                hk = detect(frames, {"id": "hk", "kind": "hist_kl", **cfg["union"]})
                cache[(seq, inj_id, L)] = (score, hk["mask"])
        print("cached", seq, flush=True)

    rows = []
    # ---------------- validation grid ----------------
    for k in cfg["grid"]["k"]:
        for h in cfg["grid"]["h"]:
            vals = []
            for seq in val:
                for inj_id in cfg["injections"]:
                    for L in [cfg["selection"]["length"]]:
                        score, hk_mask = cache[(seq, inj_id, L)]
                        mask = prune_segments(cusum_alarm(score, k, h), cfg["grid"]["min_len"])
                        fm, im = evals(mask, spans_from_mask(mask), start, L)
                        vals.append((fm["recall"], fm["precision"], fm["f1"], fm["iou"], im["interval_iou"]))
                        # union
                        umask = mask | hk_mask
                        ufm, uim = evals(umask, spans_from_mask(umask), start, L)
                        vals.append((ufm["recall"], ufm["precision"], ufm["f1"], ufm["iou"], uim["interval_iou"]))
            a = np.array(vals, dtype=float)
            n2 = len(vals) // 2
            for variant, block in (("cusum", a[0::2]), ("union", a[1::2])):
                rec = dict(split="validation", k=k, h=h, variant=variant,
                           length=cfg["selection"]["length"], injection="all", n=len(block),
                           recall=float(np.mean(block[:, 0])), precision=float(np.mean(block[:, 1])),
                           f1=float(np.mean(block[:, 2])), iou=float(np.mean(block[:, 3])),
                           interval_iou=float(np.nanmean(block[:, 4])))
                rows.append(rec)

    # selection: max F1 s.t. P>=0.60, tie higher recall
    def pick(variant):
        cand = [r for r in rows if r["split"] == "validation" and r["variant"] == variant and r["precision"] >= 0.60]
        return max(cand, key=lambda r: (r["f1"], r["recall"])) if cand else None

    best_cusum, best_union = pick("cusum"), pick("union")
    if best_union and (not best_cusum or best_union["f1"] > best_cusum["f1"]):
        chosen_variant = "union"
        chosen = best_union
    else:
        chosen_variant = "cusum"
        chosen = best_cusum
    if chosen is None:
        raise SystemExit("no validation point reaches precision >= 0.60")
    sel_k, sel_h = chosen["k"], chosen["h"]

    # ---------------- test at selected + baseline h=6 ----------------
    def test_block(variant, k, h, label):
        out = []
        for seq in test:
            for inj_id in cfg["injections"]:
                for L in lengths:
                    score, hk_mask = cache[(seq, inj_id, L)]
                    mask = prune_segments(cusum_alarm(score, k, h), cfg["grid"]["min_len"])
                    if variant == "union":
                        mask = mask | hk_mask
                    fm, im = evals(mask, spans_from_mask(mask), start, L)
                    out.append(dict(split="test", variant=label, k=k, h=h, length=L, injection=inj_id,
                                    n=1, recall=fm["recall"], precision=fm["precision"], f1=fm["f1"],
                                    iou=fm["iou"], interval_iou=im["interval_iou"]))
        return out

    test_rows = test_block(chosen_variant, sel_k, sel_h, "selected")
    test_rows += test_block("cusum", 0.5, 6.0, "baseline_h6")

    with open(os.path.join(staging, "selection.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    with open(os.path.join(staging, "test_metrics.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(test_rows)

    def agg(block, L, inj="all"):
        rs = [r for r in block if r["length"] == L and (inj == "all" or r["injection"] == inj)]
        return {m: float(np.mean([r[m] for r in rs])) for m in
                ("recall", "precision", "f1", "iou", "interval_iou")} if rs else {}

    summary = {
        "run_id": args.run_id, "status": "SUCCESS",
        "validation_sequences": val, "test_sequences": test,
        "selected": {"variant": chosen_variant, "k": sel_k, "h": sel_h,
                     "validation_len12": chosen},
        "baseline_h6_validation": next((r for r in rows if r["variant"] == "cusum"
                                        and r["k"] == 0.5 and r["h"] == 6.0), None),
        "test": {"selected_len12": agg([r for r in test_rows if r["variant"] == "selected"], 12, "all"),
                 "baseline_h6_len12": agg([r for r in test_rows if r["variant"] == "baseline_h6"], 12, "all")},
        "wall_seconds": time.time() - t0,
        "artifacts": {f: {"sha256": sha256_file(os.path.join(staging, f)),
                          "bytes": os.path.getsize(os.path.join(staging, f))}
                      for f in ("selection.csv", "test_metrics.csv")},
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(os.path.join(staging, "summary.json"), summary)
    os.rename(staging, final)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
