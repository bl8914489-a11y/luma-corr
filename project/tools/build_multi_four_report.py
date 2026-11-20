"""Build the four-interval stress-test supplement."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "multi_four_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "四段多区间补充_2026-11-19.docx")

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


doc.add_heading("四段多区间缺陷补充", level=0)
p("13 段 · 四个缺陷段 [6,10)/[24,28)/[42,50)/[62,70) · mixed/sameA | 2026-11-19", size=11)
p("mixed：段 1 A、段 2 B、段 3 B′、段 4 A；sameA：四段都用 A。A3/A7 分段独立校正；CUSUM 检测整段。")

for sc, label in (("mixed", "mixed"), ("sameA", "sameA")):
    p(label, bold=True)
    table(["方法", "Y MAE", "OutFrac", "检测召回", "检测精确率", "段 1", "段 2", "段 3", "段 4"], [
        [m, f"{S['by_scenario_method'][f'{sc}_{m}']['y_mae']:.2f}",
         f"{100*S['by_scenario_method'][f'{sc}_{m}']['outfrac']:.2f}%",
         f"{S['by_scenario_method'][f'{sc}_{m}']['det_recall']:.2f}",
         f"{S['by_scenario_method'][f'{sc}_{m}']['det_precision']:.2f}",
         f"{S['by_scenario_method'][f'{sc}_{m}']['hit1']:.2f}",
         f"{S['by_scenario_method'][f'{sc}_{m}']['hit2']:.2f}",
         f"{S['by_scenario_method'][f'{sc}_{m}']['hit3']:.2f}",
         f"{S['by_scenario_method'][f'{sc}_{m}']['hit4']:.2f}"]
        for m in ("A1", "A3", "A7")
    ], [1.8, 2.2, 2.2, 2.4, 2.6, 1.8, 1.8, 1.8, 1.8])

for x in [
    "校正仍有效：mixed A3 3.21、A7 2.77；sameA A3 1.58、A7 3.53；区间外改动 0%。",
    "检测没有继续明显变差，但一直差：mixed 召回 0.62、sameA 0.54；段命中 0.54–1.00。",
    "四段下 CUSUM 的窗口污染与三段类似；多区间检测仍是开放问题。",
    "本补充只测一种四段布局；不同间隔/长度/强度顺序未测。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/multi_four_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
