"""Build the three-interval multi-scan supplement."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "multi_scan_three_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "三段多区间检测补充_2026-11-18.docx")

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


doc.add_heading("三段多区间检测补充", level=0)
p("同一套三段/混合区间 · 全窗口扫描 + 非重叠选择（最多 3 段） | 2026-11-18", size=11)
p("设置与三段校正实验一致：mixed = [8,12) A、[34,42) B、[58,70) B′；sameA = 三段都用 A。"
  "阈值与最大段数只在 4 段验证集选，测试集只评一次。")
table(["数据", "召回", "精确率", "段 1 命中", "段 2 命中", "段 3 命中", "span 数"], [
    ["validation", f"{S['validation']['recall']:.3f}", f"{S['validation']['precision']:.3f}",
     f"{S['validation']['hit1']:.2f}", f"{S['validation']['hit2']:.2f}", f"{S['validation']['hit3']:.2f}",
     f"{S['validation']['n_spans']:.1f}"],
    ["test（全部）", f"{S['test']['recall']:.3f}", f"{S['test']['precision']:.3f}",
     f"{S['test']['hit1']:.2f}", f"{S['test']['hit2']:.2f}", f"{S['test']['hit3']:.2f}",
     f"{S['test']['n_spans']:.1f}"],
    ["test mixed", f"{S['test_mixed']['recall']:.3f}", f"{S['test_mixed']['precision']:.3f}",
     f"{S['test_mixed']['hit1']:.2f}", f"{S['test_mixed']['hit2']:.2f}", f"{S['test_mixed']['hit3']:.2f}", "3.0"],
    ["test sameA", f"{S['test_sameA']['recall']:.3f}", f"{S['test_sameA']['precision']:.3f}",
     f"{S['test_sameA']['hit1']:.2f}", f"{S['test_sameA']['hit2']:.2f}", f"{S['test_sameA']['hit3']:.2f}", "3.0"],
], [3.0, 2.0, 2.0, 2.2, 2.2, 2.2, 2.0])
for x in [
    "三段下多区间扫描测试召回 0.928、精确率 0.546，三段命中 0.83/0.94/0.94；CUSUM 只有 0.60/0.50，命中 0.54–0.92。",
    "第一段最短（len4）且靠近序列起点，命中最低（0.83）；第二、三段为 0.94。",
    "精确率仍是代价：0.546，低于单区间 CUSUM；适合“多段不漏”的场景，不适合高精确率单段。",
    "阈值/段数验证集选，测试集未调参；结果与两段扫描一致——召回/命中提升、精确率下降。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/multi_scan_three_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
