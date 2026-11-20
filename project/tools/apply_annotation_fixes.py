"""Merge the 001-005 fixes into the final annotation table and re-run natural detection."""
from __future__ import annotations

import csv
import json
import os
from collections import Counter

WS = r"F:\周四焜哥论文"
REC = os.path.join(WS, "标注", "回收")
rows = list(csv.DictReader(open(os.path.join(REC, "标注_标准化_2026-11-19.csv"), encoding="utf-8")))

FIX = {
    "clip_001": {"has_defect": "0", "start": "", "end": "", "type": "none", "severity": "", "confidence": "", "notes": "用户确认稳"},
    "clip_002": {"has_defect": "1", "start": "4", "end": "15", "type": "exposure", "severity": "4", "confidence": "3", "notes": "用户补充"},
    "clip_003": {"has_defect": "1", "start": "4", "end": "15", "type": "exposure", "severity": "4", "confidence": "3", "notes": "用户补充"},
    "clip_004": {"has_defect": "1", "start": "4", "end": "15", "type": "exposure", "severity": "4", "confidence": "3", "notes": "用户补充"},
    "clip_005": {"has_defect": "0", "start": "", "end": "", "type": "none", "severity": "", "confidence": "", "notes": "用户确认稳"},
}
for r in rows:
    if r["clip_id"] in FIX:
        r.update(FIX[r["clip_id"]])
        r["flags"] = ""
    elif r["clip_id"] in ("clip_016", "clip_018"):
        r["severity"] = ""
        r["flags"] = "稳但有严重度；已清空严重度，待确认"
    elif r["clip_id"] == "clip_091":
        r["flags"] = "一格两个区间(1-15 16-21)，只取第一个"
    elif r["clip_id"] in ("clip_099", "clip_100"):
        r["flags"] = "稳但置信度空白"

# add unresolved frame-base flag to all positives
for r in rows:
    if r["has_defect"] == "1" and "1-based" not in r["flags"]:
        r["flags"] = (r["flags"] + "; " if r["flags"] else "") + "帧号基准未确认"

out = os.path.join(REC, "标注_最终_2026-11-20.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

labeled = [r for r in rows if r["has_defect"] in ("0", "1")]
pos = [r for r in rows if r["has_defect"] == "1"]
types = Counter(r["type"] for r in pos)
lens = [int(r["end"]) - int(r["start"]) for r in pos if r["start"] and r["end"]]
summary = {"n": len(rows), "n_labeled": len(labeled), "n_positive": len(pos),
           "defect_rate": len(pos) / len(labeled), "types": dict(types),
           "median_len": sorted(lens)[len(lens) // 2] if lens else None,
           "whole_clip": sum(1 for r in pos if r["start"] and int(r["start"]) <= 1 and int(r["end"]) >= 21)}
json.dump(summary, open(os.path.join(REC, "标注_最终汇总_2026-11-20.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

lines = ["# 标注最终版（2026-11-20）", "",
         f"- 已标：{len(labeled)}/100；正例 {len(pos)}；缺陷率 {summary['defect_rate']:.1%}",
         f"- 类型：{dict(types)}", f"- 区间长度中位：{summary['median_len']}",
         f"- 几乎整段：{summary['whole_clip']}/{len(pos)}", "",
         "## 已解决", "- clip_001–005 已按用户补充并入（001/005 稳；002–004 4–15 exposure 4/3）。",
         "## 仍未确认", "- 帧号基准（0-based / 1-based）：所有正例起点 ≥1、无 0，疑似 1-based。",
         "- clip_016/018：原为稳但有严重度，已清空严重度，待确认。",
         "- clip_091：一格两个区间，只取第一个。", "- clip_099/100：稳但置信度空白。",
         "- 无第二位标注者：不做 kappa/IoU，不声称 inter-rater。"]
open(os.path.join(REC, "校验报告_2026-11-20.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(json.dumps(summary, ensure_ascii=False, indent=1))
