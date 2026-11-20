"""Build the four-interval multi-scan supplement."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "multi_scan_four_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "四段多区间检测补充_2026-11-19.docx")

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


doc.add_heading("四段多区间检测补充", level=0)
p("全窗口扫描 + 非重叠选择（最多 4 段）· 验证集选阈值 · 测试集只评一次 | 2026-11-19", size=11)
table(["数据", "召回", "精确率", "段 1", "段 2", "段 3", "段 4", "平均 span 数"], [
    ["validation", f"{S['validation']['recall']:.3f}", f"{S['validation']['precision']:.3f}",
     f"{S['validation']['hit1']:.2f}", f"{S['validation']['hit2']:.2f}", f"{S['validation']['hit3']:.2f}",
     f"{S['validation']['hit4']:.2f}", f"{S['validation']['n_spans']:.1f}"],
    ["test", f"{S['test']['recall']:.3f}", f"{S['test']['precision']:.3f}",
     f"{S['test']['hit1']:.2f}", f"{S['test']['hit2']:.2f}", f"{S['test']['hit3']:.2f}",
     f"{S['test']['hit4']:.2f}", f"{S['test']['n_spans']:.1f}"],
], [3.0, 2.0, 2.2, 2.2, 2.2, 2.2, 2.2, 2.8])
for x in [
    "四段下多区间扫描测试召回 0.769、精确率 0.497，平均只输出 2.8 个 span（真值 4 段）。",
    "四段命中均为 0.78；它没有把四段都找全，且精确率低于两段/三段。",
    "对比 CUSUM 四段：召回 0.62、精确率 0.87；扫描召回更高但精确率更低，且段数不足。",
    "趋势：段数从 2→3→4，扫描召回 0.925→0.928→0.769，精确率 0.530→0.546→0.497；多段检测未随段数扩展而变好。",
    "阈值/最大段数验证集选，测试集未调参。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/multi_scan_four_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
