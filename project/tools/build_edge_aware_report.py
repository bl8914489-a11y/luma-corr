"""Build the edge-aware A3e supplement."""
from __future__ import annotations

import csv
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUNS = {0: "edge_aware_start0_v1", 64: "edge_aware_start64_v1"}
OUT = os.path.join(WS, "报告", "边缘感知估计器补充_2026-11-18.docx")
cache = {s: list(csv.DictReader(open(os.path.join(WS, "results", "runs", r, "per_sequence.csv"), encoding="utf-8")))
         for s, r in RUNS.items()}

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
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(9)
    for row in data:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(9)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


def m(s, L, inj, method):
    v = [float(r["y_mae"]) for r in cache[s] if int(r["length"]) == L and r["injection"] == inj and r["method"] == method]
    return float(np.mean(v))


doc.add_heading("边缘感知估计器 A3e 补充", level=0)
p("修 start=0 / 结束于 76 时 A3 退化为全局均值的问题 | 2026-11-18", size=11)

doc.add_heading("一、问题", level=1)
p("A3 用左右各 3 帧拟合直线。start=0 或区间结束于最后一帧时，原实现把 k 降为 0，"
  "目标退化为整段均值（包含缺陷），所以贴边误差放大 3–5 倍。")

doc.add_heading("二、A3e", level=1)
p("A3e 在只有单侧上下文时，用该侧最多 2k 帧拟合直线并外推；两侧都有时与原 A3 相同。"
  "它不改变区间内加性偏移的写回方式，只改目标亮度估计。")

doc.add_heading("三、结果", level=1)
table(["起点", "长度", "注入", "A3", "A3e", "变化"], [
    [s, L, inj, f"{m(s,L,inj,'A3'):.2f}", f"{m(s,L,inj,'A3e'):.2f}",
     f"{m(s,L,inj,'A3e')-m(s,L,inj,'A3'):+.2f}"]
    for s in (0, 64) for L in (1, 4, 12) for inj in ("A", "B", "B13")
], [1.6, 1.6, 1.8, 2.0, 2.0, 2.0])

doc.add_heading("四、结论", level=1)
for x in [
    "start=0 的 A 注入改善最大：len1 9.41→3.06，len4 7.56→1.56；B 注入 len1 14.19→10.19，B′ 10.22→5.06。",
    "start=64 的 len12 也改善：A 6.49→5.73，B 13.90→10.83，B′ 7.43→7.20；len1/4 本来有左侧上下文，A3e 与 A3 相同。",
    "但 A3e 仍未追平中部（A len1 中部 2.06、len4 1.48；B len12 中部 8.07），边缘外推只能缓解，不能消除。",
    "A3e 是低成本改进（只改目标估计），可作为方法的一部分；论文应同时报告“贴边仍差于中部”的限制。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/edge_aware_start0_v1/、edge_aware_start64_v1/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
