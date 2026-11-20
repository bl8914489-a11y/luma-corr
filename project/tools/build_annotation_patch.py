"""Create a patch workbook and a readable validation report for the returned labels."""
from __future__ import annotations

import csv
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

WS = r"F:\周四焜哥论文"
REC = os.path.join(WS, "标注", "回收")
rows = list(csv.DictReader(open(os.path.join(REC, "标注_标准化_2026-11-19.csv"), encoding="utf-8")))
S = json.load(open(os.path.join(REC, "标注_汇总_2026-11-19.json"), encoding="utf-8"))

wb = Workbook()
ws = wb.active; ws.title = "需补与确认"
headers = ["clip_id", "问题", "has_defect", "start", "end", "type", "severity_1_5", "confidence_1_3", "notes"]
ws.append(headers)
for c in ws[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="C00000")

patch = []
for cid in ["clip_001", "clip_002", "clip_003", "clip_004", "clip_005"]:
    patch.append([cid, "标签空白，请补 0/1 及后续字段", "", "", "", "", "", "", ""])
for cid in ["clip_016", "clip_018"]:
    patch.append([cid, "标了“稳”但填了严重度“肉眼可见”；请确认：稳→清空严重度，或不稳→补区间/类型", "", "", "", "", "", "", ""])
patch.append(["clip_091", "一格填了两个区间（1-15 16-21）；请只保留主区间，其余写 notes", "", "", "", "", "", "", ""])
for cid in ["clip_099", "clip_100"]:
    patch.append([cid, "置信度空白（稳）；请补 1/2/3", "", "", "", "", "", "", ""])
patch.append(["ALL", "帧号基准确认：当前 70 个正例起点都 ≥1，没有 0，疑似 1-based；模板要求 0–23。请确认是 0-based 还是 1-based，我按你的确认统一转换。", "", "", "", "", "", "", ""])
for r in patch:
    ws.append(r)
for c in ws[1]:
    c.alignment = Alignment(horizontal="center", wrap_text=True)
for col, w in zip("ABCDEFGHI", [12, 70, 10, 8, 8, 10, 12, 12, 30]):
    ws.column_dimensions[col].width = w
ws.freeze_panes = "A2"

ws2 = wb.create_sheet("标准化_100")
cols = ["clip_id", "sequence", "clip_start", "has_defect", "start", "end", "type", "severity", "confidence", "notes", "flags"]
ws2.append(cols)
for r in rows:
    ws2.append([r[c] for c in cols])
for c in ws2[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F5597")
for col, w in zip("ABCDEFGHIJK", [10, 12, 10, 10, 8, 8, 10, 10, 12, 20, 60]):
    ws2.column_dimensions[col].width = w
ws2.freeze_panes = "A2"

ws3 = wb.create_sheet("初步统计")
stats = [
    ("已标", f"{S['n_labeled']}/100"),
    ("未标", "、".join(S["unlabeled_ids"])),
    ("正例", S["n_positive"]),
    ("缺陷率（按已标）", f"{S['defect_rate']:.1%}"),
    ("类型", json.dumps(S["types"], ensure_ascii=False)),
    ("严重度", json.dumps(S["severity"], ensure_ascii=False)),
    ("区间长度中位", S["median_len"]),
    ("起点≤1 的正例", "30/70"),
    ("终点≥21 的正例", "55/70"),
    ("几乎整段（起点≤1 且终点≥21）", "26/70"),
]
ws3.append(["指标", "值"])
for c in ws3[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F5597")
for k, v in stats:
    ws3.append([k, v])
ws3.column_dimensions["A"].width = 34; ws3.column_dimensions["B"].width = 70

ws4 = wb.create_sheet("说明")
lines = [
    "这份表只列需要你补/确认的项；不要重填 100 行。",
    "1. clip_001–005 标签空白，必须补。",
    "2. 帧号基准必须确认：当前正例起点没有 0，疑似 1-based；模板要求 0–23。",
    "3. clip_016/018 标“稳”但有严重度；clip_091 一格两个区间；clip_099/100 置信度空白。",
    "4. 原始表只有 6 列，缺少 notes/数值 severity/数值 confidence；标准化表已做映射，但请确认映射：",
    "   - 明显但不碍看 → severity 3",
    "   - 肉眼可见 → severity 4",
    "   - 非常确定 → confidence 3",
    "5. 自然闪烁有 26/70 段几乎覆盖整个 24 帧片段；这会影响与“有界单区间”合成实验的可比性，需要你确认这是有意标注。",
]
for i, t in enumerate(lines, 1):
    c = ws4.cell(row=i, column=1, value=t); c.font = Font(size=10); c.alignment = Alignment(wrap_text=True)
ws4.column_dimensions["A"].width = 120

wb.save(os.path.join(REC, "标注_需确认_2026-11-19.xlsx"))

# readable report
rep = f"""# 标注回收校验（2026-11-19）

来源：`E:/weixin/.../工作簿1(1).xlsx`

## 一、先看结论

- 收到 100 行，**已标 95，未标 5（clip_001–005）**。
- 已标里 **70 个正例，缺陷率 73.7%**；类型：exposure 29、flicker 19、gamma 17、other 5。
- 严重度：肉眼可见 51（映射 4）、明显但不碍看 19（映射 3）；全部“非常确定”（映射 3）。
- 区间长度中位 **15 帧**；**26/70 段几乎覆盖整个 24 帧片段**（起点≤1 且终点≥21）。

## 二、必须修正/确认

1. **clip_001–005 标签空白**，必须补。
2. **帧号基准**：70 个正例起点都 ≥1、没有 0，疑似 1-based；模板要求 0–23。请确认，我按确认统一转换；未确认前统计按原值。
3. **clip_016 / clip_018**：标“稳”但填了严重度“肉眼可见”；请清空严重度或改“不稳”并补区间/类型。
4. **clip_091**：一格填了两个区间“1-15 16-21”；请只保留主区间，其余写 notes。
5. **clip_099 / clip_100**：置信度空白（稳）；请补 1/2/3。
6. 原始表只有 6 列，缺 notes、数值 severity、数值 confidence；标准化表已映射，但请确认：
   - 明显但不碍看 → severity 3
   - 肉眼可见 → severity 4
   - 非常确定 → confidence 3
7. 类型有尾部空格（gamma / exposure / flicker 后带空格），已自动 strip。

## 三、语义风险

自然闪烁里 **26/70 段几乎覆盖整个片段**，中位长度 15 帧；这说明很多片段是“整段都在闪/漂”，
而不是我们合成实验定义的“一个有界区间”。这会直接影响与合成注入的可比性：
- 不能把自然标注直接当作“单区间”真值去算 IoU；
- 论文里要么改成“整段是否有缺陷 + 主区间”双标签，要么只取明确有界（长度≤12 且不贴边）的子集。
这一条需要你确认：这些“整段”是你有意标的，还是把整段闪烁都算进去了。

## 四、初步统计

| 指标 | 值 |
|---|---|
| 已标 | 95/100 |
| 正例 | 70 |
| 缺陷率 | 73.7% |
| 类型 | exposure 29 / flicker 19 / gamma 17 / other 5 |
| 严重度 | 4:51 / 3:19 |
| 区间长度中位 | 15 |
| 起点≤1 | 30/70 |
| 终点≥21 | 55/70 |
| 几乎整段 | 26/70 |

按序列正例：sailboat 1/8、paint 3/8、book 7/8、yoga 8/8、asteroids 7/7…差异很大，说明自然闪烁的序列依赖性很强。

## 五、下一步

1. 你补/确认 `标注_需确认_2026-11-19.xlsx`；
2. 找第二位标注者，至少双标 20%（20 个片段），算 kappa/IoU；
3. 确认帧号基准后，我再决定：
   - 用“整段是否有缺陷”做二分类；
   - 或只取有界区间子集做 IoU；
4. 单标注结果先不写进论文主表，只作为预实验。
"""
open(os.path.join(REC, "校验报告_2026-11-19.md"), "w", encoding="utf-8").write(rep)
print("saved patch and report")
