"""Apply the confirmed frame-base decisions and rerun natural detection."""
from __future__ import annotations

import csv
import json
import os

WS = r"F:\周四焜哥论文"
REC = os.path.join(WS, "标注", "回收")
SRC = os.path.join(REC, "标注_最终_2026-11-20.csv")
OUT = os.path.join(REC, "标注_最终_确认_2026-11-20.csv")
rows = list(csv.DictReader(open(SRC, encoding="utf-8")))

for r in rows:
    r["frame_base"] = "1based->0based"
    if r["has_defect"] == "1":
        s = int(r["start"]); e = int(r["end"])
        if r["clip_id"] == "clip_091":
            s0, e0 = 0, 21
            r["flags"] = (r["flags"] + "; " if r["flags"] else "") + "两段1-15/16-21合并为主区间1-21"
        else:
            s0, e0 = max(0, s - 1), min(24, e)
            r["flags"] = (r["flags"] + "; " if r["flags"] else "") + "1-based转0-based"
        r["start0"], r["end0"] = s0, e0
        # keep start/end as 0-based inclusive so the existing 0-based branch reconstructs [s0,e0)
        r["start"], r["end"] = s0, max(s0, e0 - 1)
    else:
        r["start0"], r["end0"] = "", ""
    if r["clip_id"] in ("clip_016", "clip_018"):
        r["severity"] = ""
        r["flags"] = (r["flags"] + "; " if r["flags"] else "") + "稳，严重度清空"
    if r["clip_id"] in ("clip_099", "clip_100"):
        r["flags"] = (r["flags"] + "; " if r["flags"] else "") + "稳，置信度留空"

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

pos = [r for r in rows if r["has_defect"] == "1"]
lens = [int(r["end0"]) - int(r["start0"]) for r in pos]
summary = {"n": len(rows), "n_labeled": len(rows), "n_positive": len(pos),
           "defect_rate": len(pos) / len(rows), "median_len": sorted(lens)[len(lens) // 2],
           "whole_clip": sum(1 for r in pos if int(r["start0"]) <= 1 and int(r["end0"]) >= 21),
           "frame_base": "1based converted to 0based half-open"}
json.dump(summary, open(os.path.join(REC, "标注_确认汇总_2026-11-20.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
