"""Validate and normalise the first returned annotation workbook."""
from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict

import openpyxl

WS = r"F:\周四焜哥论文"
SRC = r"E:\weixin\新建文件2\xwechat_files\wxid_cflu5fq6m23i12_3c39\msg\file\2026-11\工作簿1(1).xlsx"
OUT = os.path.join(WS, "标注", "回收")
os.makedirs(OUT, exist_ok=True)

SEV = {"明显但不碍看": 3, "肉眼可见": 4}
CONF = {"非常确定": 3, "较确定": 2, "不确定": 1}


def main():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    header = rows[0]
    data = [r for r in rows[1:] if r[0]]
    index = {r["clip_id"]: r for r in csv.DictReader(open(os.path.join(WS, "标注", "clip_index.csv"), encoding="utf-8"))}

    issues = []
    norm = []
    ids = [str(r[0]).strip() for r in data]
    if len(data) != 100:
        issues.append(f"数据行数 {len(data)}，应为 100")
    if len(set(ids)) != len(ids):
        issues.append("clip_id 有重复")
    missing_ids = sorted(set(index) - set(ids))
    extra_ids = sorted(set(ids) - set(index))
    if missing_ids:
        issues.append(f"缺少 clip_id: {missing_ids}")
    if extra_ids:
        issues.append(f"多余 clip_id: {extra_ids}")
    if header[1:] != (None,) * 5:
        issues.append(f"表头不完整: {header}")

    for r in data:
        cid = str(r[0]).strip()
        label = (r[1] or "").strip()
        raw_int = (r[2] or "").strip()
        typ = (r[3] or "").strip().lower()
        sev_raw = (r[4] or "").strip()
        conf_raw = (r[5] or "").strip()
        meta = index.get(cid, {})
        row = {"clip_id": cid, "sequence": meta.get("sequence", ""), "clip_start": meta.get("clip_start", ""),
               "has_defect": "", "start": "", "end": "", "type": "", "severity": "", "confidence": "",
               "notes": "", "flags": ""}
        flags = []
        if label not in ("稳", "不稳"):
            flags.append(f"标签非法({label!r})")
        else:
            row["has_defect"] = 0 if label == "稳" else 1
        # parse one or more intervals, keep the first and flag extras
        spans = re.findall(r"(\d+)\s*-\s*(\d+)", raw_int)
        if row["has_defect"] == 1:
            if not spans:
                flags.append("不稳但区间为空/不可解析")
            else:
                s, e = int(spans[0][0]), int(spans[0][1])
                row["start"], row["end"] = s, e
                if not (0 <= s < e <= 23):
                    flags.append(f"区间越界/反序({s}-{e})")
                if len(spans) > 1:
                    flags.append(f"一段填了多个区间({raw_int})，只取第一个")
                if s == 0:
                    flags.append("出现 0 起点")
        else:
            if raw_int:
                flags.append(f"稳但有区间({raw_int})")
            if sev_raw:
                flags.append(f"稳但有严重度({sev_raw})")
        if row["has_defect"] == 1:
            if typ not in ("flicker", "exposure", "gamma", "other"):
                flags.append(f"类型非法/带空格({typ!r})")
            row["type"] = typ
            if sev_raw not in SEV:
                flags.append(f"严重度文本未映射({sev_raw!r})")
            else:
                row["severity"] = SEV[sev_raw]
            if conf_raw not in CONF:
                flags.append(f"置信度缺失/未映射({conf_raw!r})")
            else:
                row["confidence"] = CONF[conf_raw]
        else:
            if typ:
                flags.append(f"稳但填了类型({typ})")
            if conf_raw:
                row["confidence"] = CONF.get(conf_raw, "")
                if conf_raw not in CONF:
                    flags.append(f"置信度未映射({conf_raw!r})")
        row["notes"] = sev_raw
        row["flags"] = "; ".join(flags)
        if flags:
            issues.append(f"{cid}: " + "; ".join(flags))
        norm.append(row)

    # off-by-one check: no interval starts at 0 anywhere
    starts = [r["start"] for r in norm if r["has_defect"] == 1 and r["start"] != ""]
    if starts and min(starts) >= 1:
        issues.append("所有正例起点都 ≥1，疑似使用 1-based 帧号（模板要求 0–23）；本次未自动转换，需你确认。")

    with open(os.path.join(OUT, "标注_标准化_2026-11-19.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["clip_id", "sequence", "clip_start", "has_defect",
                                           "start", "end", "type", "severity", "confidence", "notes", "flags"])
        w.writeheader(); w.writerows(norm)

    labeled = [r for r in norm if r["has_defect"] in (0, 1)]
    unlabeled = [r["clip_id"] for r in norm if r["has_defect"] not in (0, 1)]
    pos = [r for r in norm if r["has_defect"] == 1]
    types = Counter(r["type"] for r in pos)
    sev = Counter(r["severity"] for r in pos)
    lens = [r["end"] - r["start"] for r in pos if r["start"] != "" and r["end"] != "" and r["end"] > r["start"]]
    per_seq = defaultdict(lambda: [0, 0])
    for r in norm:
        per_seq[r["sequence"]][0] += 1
        if r["has_defect"] == 1:
            per_seq[r["sequence"]][1] += 1
    summary = {"n": len(norm), "n_labeled": len(labeled), "n_unlabeled": len(unlabeled),
               "unlabeled_ids": unlabeled, "n_positive": len(pos),
               "defect_rate": len(pos) / max(len(labeled), 1),
               "types": dict(types), "severity": {str(k): v for k, v in sev.items()},
               "median_len": sorted(lens)[len(lens) // 2] if lens else None,
               "per_sequence": {k: {"n": v[0], "pos": v[1]} for k, v in per_seq.items()}}
    json.dump(summary, open(os.path.join(OUT, "标注_汇总_2026-11-19.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    lines = ["# 标注回收校验（2026-11-19）", "", f"来源：`{SRC}`", "",
             f"- 数据行：{len(data)}（应为 100）", f"- 已标：{len(labeled)}，未标：{len(unlabeled)}（{unlabeled}）"
             f"- 正例：{len(pos)}，缺陷率 {len(pos)/max(len(labeled),1):.1%}",
             f"- 类型分布：{dict(types)}", f"- 严重度分布：{dict(sev)}",
             f"- 区间长度中位数：{summary['median_len']}", "", "## 逐条问题", ""]
    if issues:
        lines += [f"- {x}" for x in issues]
    else:
        lines.append("- 无")
    lines += ["", "## 按序列", "", "| sequence | clips | positive |", "|---|---:|---:|"]
    for k, v in sorted(per_seq.items()):
        lines.append(f"| {k} | {v[0]} | {v[1]} |")
    open(os.path.join(OUT, "校验报告_2026-11-19.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("issues", len(issues))
    for x in issues[:12]:
        print(" -", x)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
