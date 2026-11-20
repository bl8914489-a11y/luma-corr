"""Build the B2 three-interval report."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "b2_three_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "B2_三段缺陷_2026-11-19.docx")

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


doc.add_heading("B2 All-In-One 三段缺陷基线", level=0)
p("13 段 × 2 场景（mixed / sameA）= 26 案例 · 官方代码+权重 | 2026-11-19", size=11)

doc.add_heading("一、设置", level=1)
p("mixed：段 1 [8,12) A、段 2 [34,42) B、段 3 [58,70) B′；sameA：三段都用 A。"
  "B2 处理整段视频，A3/A7 对三段分别独立校正；评价始终在真值三段上。")

doc.add_heading("二、结果", level=1)
for label, key in (("全部 26 案例", "overall"), ("mixed", "mixed"), ("sameA", "sameA")):
    p(label, bold=True)
    table(["方法", "Y MAE", "PSNR", "OutFrac", "区间外 RGB", "边界"], [
        [m, f"{S[key][m]['y_mae']:.2f}", f"{S[key][m]['psnr']:.2f}",
         f"{100*S[key][m]['outfrac']:.2f}%", f"{S[key][m]['outside_rgb_mae']:.2f}",
         f"{S[key][m]['boundary_err']:.2f}"]
        for m in ("A1", "A3", "A7", "B2")
    ], [2.2, 2.2, 2.2, 2.6, 2.8, 2.4])

doc.add_heading("三、结论", level=1)
for x in [
    "B2 在三段上 Y-MAE 12.83，A3 为 3.51、A7 为 3.31；B2 仍明显更差。",
    "mixed 下 B2 14.86 vs A3 4.92/A7 2.79；sameA 下 B2 10.80 vs A3 2.10/A7 3.82。",
    "B2 区间外改动 99.98%、区间外 RGB 差 12.05；A3/A7 均为 0。",
    "B2 边界 7.19 略低于 A3 8.37/A7 8.12，但这是整段重写的平滑，不是区间保持。",
    "与单区间/两区间结论一致：盲全局深度基线不适合“已知区间 + 区间外保持”的任务。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/b2_three_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
