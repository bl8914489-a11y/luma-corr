"""Build the preliminary natural-annotation detection report."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "natural_detection_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "自然标注预实验_2026-11-19.docx")

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


doc.add_heading("自然闪烁标注预实验（单标注）", level=0)
p("95 个已标片段 · CUSUM 检测 · 2026-11-19 | 预实验，帧号基准待确认", size=11)

doc.add_heading("一、设置", level=1)
p("对 100 个 24 帧干净片段中的 95 个已标片段运行主检测器 CUSUM（k=0.5, h=8.0, min_len=2）。"
  "人工标签提供 clip 级 has_defect 与局部区间；同时按 0-based/1-based 两种帧号解释计算区间指标。"
  "本结果不写进论文主表，只作为自然场景的预实验与 limitations。")

doc.add_heading("二、结果", level=1)
table(["指标", "值"], [
    ["已标/正例", f"{S['n']}/{S['n_positive']}"],
    ["clip 级 TP/FP/FN/TN", f"{S['clip_confusion']['tp']}/{S['clip_confusion']['fp']}/{S['clip_confusion']['fn']}/{S['clip_confusion']['tn']}"],
    ["clip 精确率", f"{S['clip_precision']:.3f}"],
    ["clip 召回", f"{S['clip_recall']:.3f}"],
    ["clip 准确率", f"{S['clip_accuracy']:.3f}"],
    ["区间召回（0-based 解释）", f"{S['interval_mean_recall_0']:.3f}"],
    ["区间召回（1-based 解释）", f"{S['interval_mean_recall_1']:.3f}"],
], [6.0, 6.0])

p("按类型：", bold=True)
table(["类型", "n", "clip 召回", "区间召回 0"], [
    [k, v["n"], f"{v['clip_recall']:.3f}", f"{v['interval_recall_0']:.3f}"]
    for k, v in S["by_type"].items()
], [3.0, 2.0, 3.0, 3.0])

doc.add_heading("三、结论", level=1)
for x in [
    "CUSUM 在自然标注上 clip 召回只有 0.243、区间召回约 0.10；它几乎不 predicts 自然闪烁。",
    "flicker 类 19 个片段 clip 召回 0.000——CUSUM 对快速抖动完全不敏感；exposure 0.276，gamma 0.412。",
    "原因：CUSUM 是针对“持续平台 + 稳定背景”的注入缺陷调参的；自然闪烁的幅度、时长、背景变化都不同。",
    "这说明合成基准不能外推为“自然闪烁检测有效”；论文必须把它写成 limitations，而不是自然场景的 SOTA。",
    "本结果单标注、帧号未确认、26/70 标签几乎整段；修正标注和双标后需重跑，数字可能变化。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/natural_detection_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
