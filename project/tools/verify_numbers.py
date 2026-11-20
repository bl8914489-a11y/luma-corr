"""Freeze and verify every headline number against the run artifacts.

Writes results/FREEZE_2026-11-17.json with:
  * the recomputed value, tolerance, PASS/FAIL for each headline claim,
  * SHA-256 of the key CSVs and reports.
The paper may only quote numbers that pass here.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
from docx import Document

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT = os.environ.get("FREEZE_OUT", os.path.join(WS, "results", "FREEZE_2026-11-17.json"))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def docx_text(path):
    d = Document(path)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return "\n".join(parts)


def check(checks, name, value, expected, tol, unit=""):
    ok = abs(float(value) - float(expected)) <= tol
    checks.append({"name": name, "value": round(float(value), 4), "expected": expected,
                   "tolerance": tol, "unit": unit, "pass": bool(ok)})
    return ok


def main():
    checks = []
    # ---------- Tier A: dev-3 interval Y MAE ----------
    rows = read(os.path.join(WS, "results", "runs", "tierA_matrix_v1", "per_sequence.csv"))
    dev = {"sailboat", "book", "horse"}
    def devm(inj, L, m):
        v = [float(r["y_mae"]) for r in rows if r["injection"] == inj and int(r["length"]) == L
             and r["method"] == m and r["sequence"] in dev]
        return float(np.mean(v))
    expected_a3 = {("A", 1): 1.030, ("A", 4): 0.728, ("A", 12): 0.760,
                   ("B", 1): 8.654, ("B", 4): 7.873, ("B", 12): 7.892,
                   ("B13", 1): 3.784, ("B13", 4): 3.013, ("B13", 12): 3.182}
    for (inj, L), exp in expected_a3.items():
        check(checks, f"A3 {inj} len{L} dev3 Y MAE", devm(inj, L, "A3"), exp, 0.06)
    check(checks, "A1 A len1 dev3 Y MAE", devm("A", 1, "A1"), 19.905, 0.05)
    check(checks, "A2 B len1 dev3 Y MAE", devm("B", 1, "A2"), 8.839, 0.05)
    # clipping
    def clipval(seq, inj):
        r = [x for x in rows if x["sequence"] == seq and x["injection"] == inj
             and int(x["length"]) == 1 and x["method"] == "A3"][0]
        return 100 * float(r["correction_clip_fraction"])
    for seq, exp in (("sailboat", 4.53), ("book", 5.38), ("horse", 3.43)):
        check(checks, f"B clipping {seq}", clipval(seq, "B"), exp, 0.02, "%")

    # ---------- RQ3 v2 + threshold test ----------
    det = read(os.path.join(WS, "results", "runs", "rq3_detection_v2", "per_condition.csv"))
    def detm(det_id, L, inj):
        v = [float(r["recall"]) for r in det if r["detector"] == det_id and int(r["length"]) == L
             and r["injection"] == inj]
        return float(np.mean(v))
    for inj, exp in (("A", 0.795), ("B", 0.923), ("B13", 0.756)):
        check(checks, f"CUSUM len12 recall {inj}", detm("hist_kl_cusum", 12, inj), exp, 0.01)
    thr = json.load(open(os.path.join(WS, "results", "runs", "rq3_threshold_v1", "summary.json"),
                         encoding="utf-8"))
    check(checks, "test len12 recall (selected)", thr["test"]["selected_len12"]["recall"], 0.744, 0.01)
    check(checks, "test len12 precision (selected)", thr["test"]["selected_len12"]["precision"], 0.641, 0.01)
    check(checks, "validation len12 recall", thr["selected"]["validation_len12"]["recall"], 0.965, 0.01)

    # ---------- test e2e ----------
    e2e = json.load(open(os.path.join(WS, "results", "runs", "rq3_e2e_test_v1", "summary.json"),
                         encoding="utf-8"))
    check(checks, "test e2e reduction", e2e["mean_reduction_detected"], 0.655, 0.01)
    check(checks, "test e2e outFrac", e2e["mean_outfrac_detected"], 0.0401, 0.005)

    # ---------- B2 ----------
    b2 = json.load(open(os.path.join(WS, "results", "runs", "b2_len12_v1", "summary.json"),
                        encoding="utf-8"))["interval_mean"]
    check(checks, "B2 interval Y MAE", b2["B2_all_in_one"]["y_mae"], 12.48, 0.05)
    check(checks, "A3 interval Y MAE (B2 subset)", b2["A3"]["y_mae"], 4.84, 0.05)
    check(checks, "B2 outFrac", b2["B2_all_in_one"]["outfrac"], 0.9996, 0.001)
    check(checks, "B2 outside RGB MAE", b2["B2_all_in_one"]["outside_rgb_mae"], 9.79, 0.05)

    # ---------- report text contains the numbers ----------
    main_txt = docx_text(os.path.join(WS, "报告", "实验执行报告_2026-11-17.docx"))
    rq3_txt = docx_text(os.path.join(WS, "报告", "RQ3_D1D2补充实验_2026-11-17.docx"))
    b2_txt = docx_text(os.path.join(WS, "报告", "B2_All-In-One补充实验_2026-11-18.docx"))
    man_txt = docx_text(os.path.join(WS, "paper", "manuscript_draft_2026-11-17.docx"))
    text_checks = [
        ("main report has test recall 0.744", "0.744" in main_txt),
        ("main report has test e2e 65.5%", "65.5%" in main_txt),
        ("main report has B2 12.48", "12.48" in main_txt),
        ("RQ3 report has 0.744", "0.744" in rq3_txt),
        ("RQ3 report has 4.01%", "4.01%" in rq3_txt),
        ("B2 report has 12.48", "12.48" in b2_txt),
        ("B2 report has 9.79", "9.79" in b2_txt),
        ("manuscript has test recall 0.744", "0.744" in man_txt),
        ("manuscript has B2 12.48", "12.48" in man_txt),
        ("manuscript has B2 99.95%", "99.95%" in man_txt),
    ]
    for name, ok in text_checks:
        checks.append({"name": name, "value": bool(ok), "expected": True, "tolerance": 0,
                       "pass": bool(ok)})

    # ---------- test count ----------
    test_log = open(os.path.join(WS, "results", "tests", "unittest.log"), encoding="utf-8-sig").read()
    checks.append({"name": "unit test count 37", "value": "Ran 37 tests" in test_log,
                   "expected": True, "tolerance": 0, "pass": "Ran 37 tests" in test_log})

    artifacts = {}
    for p in [
        "results/runs/tierA_matrix_v1/per_sequence.csv",
        "results/runs/rq3_detection_v2/per_condition.csv",
        "results/runs/rq3_threshold_v1/test_metrics.csv",
        "results/runs/rq3_e2e_test_v1/per_condition.csv",
        "results/runs/b2_all_in_one_v1/per_case.csv",
        "报告/实验执行报告_2026-11-17.docx",
        "报告/RQ3_D1D2补充实验_2026-11-17.docx",
        "报告/B2_All-In-One补充实验_2026-11-18.docx",
    ]:
        artifacts[p] = {"sha256": sha(os.path.join(WS, p)), "bytes": os.path.getsize(os.path.join(WS, p))}

    failed = [c for c in checks if not c["pass"]]
    out = {
        "freeze_id": "2026-11-17",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failed else "FAIL",
        "n_checks": len(checks), "n_failed": len(failed),
        "checks": checks, "failed": failed, "artifacts": artifacts,
        "note": "Only numbers passing this freeze may be quoted in the paper. "
                "Changing a number requires a new freeze id.",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"status": out["status"], "checks": len(checks), "failed": len(failed)},
                     ensure_ascii=False))
    for c in failed:
        print("FAIL", c)
    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()
