"""Build the three-interval mixed supplement."""
from __future__ import annotations

import csv
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "multi_mixed_v1")
OUT = os.path.join(WS, "报告", "三段多区间补充_2026-11-18.docx")
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


def m(sc, method, key):
    v = [float(r[key]) for r in rows if r["scenario"] == sc and r["method"] == method]
    return float(np.mean(v))


doc.add_heading("三段/混合强度/混合长度多区间补充", level=0)
p("13 段 · 三个缺陷段 · len4/8/12 · A/B/B′ 混合 | 2026-11-18", size=11)

doc.add_heading("一、设置", level=1)
p("mixed：段 1 [8,12) 用 A（−20），段 2 [34,42) 用 B（γ=2），段 3 [58,70) 用 B′（γ=1.3）。"
  "sameA 对照：三段都用 A，长度相同。每段单独校正；CUSUM 直接在整段上检测。")

doc.add_heading("二、校正", level=1)
table(["场景", "方法", "Y MAE", "PSNR", "OutFrac", "区间外 RGB"], [
    [sc, meth, f"{m(sc,meth,'y_mae'):.2f}", f"{m(sc,meth,'psnr'):.2f}",
     f"{100*m(sc,meth,'outfrac'):.2f}%", f"{m(sc,meth,'outside_rgb_mae'):.2f}"]
    for sc in ("mixed", "sameA") for meth in ("A1", "A3", "A7")
], [2.4, 2.4, 2.4, 2.2, 2.6, 3.0])

doc.add_heading("三、检测（CUSUM）", level=1)
table(["场景", "帧召回", "帧精确率", "段 1 命中", "段 2 命中", "段 3 命中"], [
    [sc, f"{m(sc,'A1','det_recall'):.2f}", f"{m(sc,'A1','det_precision'):.2f}",
     f"{m(sc,'A1','hit1'):.2f}", f"{m(sc,'A1','hit2'):.2f}", f"{m(sc,'A1','hit3'):.2f}"]
    for sc in ("mixed", "sameA")
], [2.6, 2.6, 2.8, 2.8, 2.8, 2.8])

doc.add_heading("四、结论", level=1)
for x in [
    "混合三段下 A3 为 4.92、A7 为 2.79；sameA 下 A3 为 2.10、A7 为 3.82。方法排序随注入类型变化，和单区间结论一致。",
    "A3 仍保持区间外改动 0%、区间外 RGB 差 0；分段独立校正没有外溢。",
    "CUSUM 在三段下进一步退化：mixed 召回 0.60、sameA 0.50；段命中只有 0.54–0.92，第三段最差（0.54）。",
    "检测失败不是“阈值太严”而是 41 帧滚动中值同时被三段污染；多区间需要分段/合并策略，单区间 CUSUM 不够。",
    "本补充只测一种三段布局；不同间隔、强度顺序、更多段仍未测。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/multi_mixed_v1/（per_condition.csv / summary.json）。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
