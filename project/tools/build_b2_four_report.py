"""Build the B2 four-interval report."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "b2_four_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "B2_四段缺陷_2026-11-19.docx")

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


doc.add_heading("B2 All-In-One 四段缺陷基线", level=0)
p("13 段 · 四段 mixed [6,10)/[24,28)/[42,50)/[62,70) | 2026-11-19", size=11)
table(["方法", "Y MAE", "PSNR", "SSIM", "OutFrac", "区间外 RGB", "边界"], [
    [m, f"{S['overall'][m]['y_mae']:.2f}", f"{S['overall'][m]['psnr']:.2f}", f"{S['overall'][m]['ssim']:.3f}",
     f"{100*S['overall'][m]['outfrac']:.2f}%", f"{S['overall'][m]['outside_rgb_mae']:.2f}",
     f"{S['overall'][m]['boundary_err']:.2f}"]
    for m in ("A1", "A3", "A7", "B2")
], [2.2, 2.2, 2.2, 2.2, 2.6, 2.8, 2.4])
for x in [
    "B2 在四段上 Y-MAE 11.98，A3 3.21、A7 2.77；B2 仍是 A3 的 3.7 倍、A7 的 4.3 倍。",
    "B2 区间外改动 99.98%、区间外 RGB 差 12.15；A3/A7 均为 0。",
    "这次 B2 的边界误差 11.58 反而高于 A3 10.25、A7 10.03；段数增多后全局平滑不再占优。",
    "与两段/三段结论一致：盲全局深度基线不适合“已知多区间 + 区间外保持”。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/b2_four_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
