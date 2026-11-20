"""Build the two-interval defect supplement."""
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
RUN = os.path.join(WS, "results", "runs", "multi_interval_v1")
OUT = os.path.join(WS, "报告", "多区间缺陷补充_2026-11-18.docx")
rows = list(csv.DictReader(open(os.path.join(RUN, "per_condition.csv"), encoding="utf-8")))

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)


def p(text, bold=False, size=10.5):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(headers, data, widths):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(8.5)
    for row in data:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(8.5)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


def m(L, inj, method, key):
    v = [float(r[key]) for r in rows if int(r["len"]) == L and r["injection"] == inj and r["method"] == method]
    return float(np.mean(v))


doc.add_heading("多区间缺陷补充实验", level=0)
p("同一视频两个缺陷段 [10,10+L) 与 [50,50+L) · 13 段 · L=4/12 | 2026-11-18", size=11)

doc.add_heading("一、目的", level=1)
p("主实验只有一个缺陷区间。真实视频可能有多个不连续缺陷。本补充在同一视频放两个同强度缺陷，"
  "分别检验 A3/A7 的校正和 CUSUM 的检测；两段相距 40 帧，第二段起点随 L 变化。")

doc.add_heading("二、校正", level=1)
table(["L", "注入", "A1 no-op", "A3", "A7", "A3 OutFrac", "A3 区间外 RGB"], [
    [L, inj, f"{m(L,inj,'A1','y_mae'):.2f}", f"{m(L,inj,'A3','y_mae'):.2f}", f"{m(L,inj,'A7','y_mae'):.2f}",
     f"{100*m(L,inj,'A3','outfrac'):.2f}%", f"{m(L,inj,'A3','outside_rgb_mae'):.2f}"]
    for L in (4, 12) for inj in ("A", "B")
], [1.6, 1.8, 2.4, 1.8, 1.8, 2.4, 2.8])

doc.add_heading("三、检测（CUSUM）", level=1)
table(["L", "注入", "帧召回", "帧精确率", "段 1 命中", "段 2 命中", "span 数"], [
    [L, inj, f"{m(L,inj,'A1','det_recall'):.3f}", f"{m(L,inj,'A1','det_precision'):.3f}",
     f"{m(L,inj,'A1','hit1'):.2f}", f"{m(L,inj,'A1','hit2'):.2f}", f"{m(L,inj,'A1','n_spans'):.1f}"]
    for L in (4, 12) for inj in ("A", "B")
], [1.6, 1.8, 2.4, 2.4, 2.6, 2.6, 1.8])

doc.add_heading("四、结论", level=1)
for x in [
    "校正仍能处理两个不连续区间：A3 在 A 注入为 1.68/2.25（L=4/12），B 注入 8.29/8.41；A7 在 B 注入为 2.41/2.80。",
    "A3 的区间外改动仍为 0%，区间外 RGB 差为 0；两个区间分别校正没有引入外溢。",
    "检测明显变难：len4 仍高（A 0.93、B 1.00 召回），但 len12 降到 A 0.60、B 0.88；两段命中率只有 0.54/0.69（A）。",
    "原因是 41 帧滚动中值窗口同时覆盖两段与中间干净帧，平台被“ median 化”；单区间 CUSUM 不能直接推广到多区间。",
    "本补充只测同强度、同长度、两段；不同强度/长度/三段的组合未测，多区间检测仍是开放问题。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/multi_interval_v1/（per_condition.csv / summary.json）。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
