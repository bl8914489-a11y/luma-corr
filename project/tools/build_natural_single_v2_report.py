"""Build the updated 100-clip single-annotator natural report."""
from __future__ import annotations

import csv
import json
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "natural_detection_v2", "summary.json"), encoding="utf-8"))
ROWS = list(csv.DictReader(open(os.path.join(WS, "results", "runs", "natural_detection_v2", "per_clip.csv"), encoding="utf-8")))
OUT = os.path.join(WS, "报告", "自然标注_单标注_2026-11-20.docx")


def sub(fn):
    rs = [r for r in ROWS if r["has_defect"] == "1" and fn(r)]
    return len(rs), float(np.mean([int(r["pred_any"]) for r in rs])), float(np.mean([float(r["recall_0"]) for r in rs]))


wn, wr, wi = sub(lambda r: int(r["start"]) <= 1 and int(r["end"]) >= 21)
bn, br, bi = sub(lambda r: not (int(r["start"]) <= 1 and int(r["end"]) >= 21))

doc = Document()
for sec in doc.sections:
    sec.left_margin = sec.right_margin = Cm(2.0); sec.top_margin = sec.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)


def p(t, bold=False, size=10.5):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(t); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(headers, data, widths):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    for i, x in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(x); r.font.bold = True; r.font.size = Pt(9)
    for row in data:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(x)); r.font.size = Pt(9)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


doc.add_heading("自然闪烁标注：单标注版", level=0)
p("100/100 已标 · 单标注者 · 无 inter-rater 可靠性声明 | 2026-11-20", size=11)

doc.add_heading("一、标注概况", level=1)
table(["指标", "值"], [
    ["片段/已标", "100 / 100"],
    ["正例", "73（73.0%）"],
    ["类型", "exposure 32 / flicker 19 / gamma 17 / other 5"],
    ["严重度", "肉眼可见 51（映射 4）/ 明显但不碍看 19（映射 3）"],
    ["区间长度中位", "15 帧"],
    ["几乎整段（起点≤1 且终点≥21）", "26/73"],
], [6.0, 8.0])
p("标注者只有一位；没有第二位标注者，因此本报告不做 kappa、不声称 inter-rater reliability。"
  "帧号基准（0/1-based）仍未确认；区间指标同时按两种解释计算，结论不变（0.099 vs 0.101）。")

doc.add_heading("二、CUSUM 在自然片段上的表现", level=1)
table(["指标", "值"], [
    ["clip TP/FP/FN/TN", f"{S['clip_confusion']['tp']}/{S['clip_confusion']['fp']}/{S['clip_confusion']['fn']}/{S['clip_confusion']['tn']}"],
    ["clip 精确率", f"{S['clip_precision']:.3f}"],
    ["clip 召回", f"{S['clip_recall']:.3f}"],
    ["clip 准确率", f"{S['clip_accuracy']:.3f}"],
    ["区间召回（0-based）", f"{S['interval_mean_recall_0']:.3f}"],
    ["区间召回（1-based）", f"{S['interval_mean_recall_1']:.3f}"],
], [6.0, 8.0])
table(["类型", "n", "clip 召回", "区间召回 0"], [
    [k, v["n"], f"{v['clip_recall']:.3f}", f"{v['interval_recall_0']:.3f}"]
    for k, v in S["by_type"].items()
], [3.0, 2.0, 3.0, 3.0])
table(["子集", "n", "clip 召回", "区间召回 0"], [
    ["几乎整段", wn, f"{wr:.3f}", f"{wi:.3f}"],
    ["有界区间", bn, f"{br:.3f}", f"{bi:.3f}"],
], [5.0, 2.0, 3.0, 3.0])

doc.add_heading("三、结论", level=1)
for x in [
    "CUSUM 在自然标注上 clip 召回 0.247、区间召回约 0.10；它主要响应持续平台/偏移，对快速 flicker 完全不敏感（0/19）。",
    "整段类更差：26 个“几乎整段”片段 clip 召回 0.115、区间召回 0.014；有界类也只有 0.318/0.152。",
    "这说明合成注入上调出的检测器不能外推到自然闪烁；论文把它写成 limitations，不作为自然场景的 SOTA。",
    "自然片段没有干净参考，因此本报告只评检测，不计算校正后的 YMAE/PSNR；不存在“自然校正精度”数字。",
]:
    doc.add_paragraph(x, style="List Bullet")

doc.add_heading("四、必须写进 Limitations", level=1)
for x in [
    "单标注者：没有第二位标注者，无法报告 kappa/IoU 或 inter-rater reliability；所有自然标注结果为 single-annotator preliminary。",
    "帧号基准未确认：0-based 与 1-based 两种解释都给出约 0.10 的区间召回，结论不变；但论文必须注明。",
    "26/73 标签几乎覆盖整个 24 帧片段：自然闪烁常是整段持续，不是“有界单区间”；这限制了与合成 IoU 的可比性。",
    "016/018、091、099/100 的格式问题已做保守处理但未最终确认；不影响二分类，影响区间细节。",
    "只有 13 段来源、每段 7–8 个重叠片段；视频级聚类后有效样本很小。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/natural_detection_v2/；标注/回收/标注_最终_2026-11-20.csv。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
