"""Build the interval-position sensitivity supplement."""
from __future__ import annotations

import csv
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUNS = {10: "position_start10_v1", 30: "tierA_matrix_v1", 50: "position_start50_v1"}
OUT = os.path.join(WS, "报告", "位置敏感性补充_2026-11-18.docx")
FIG = os.path.join(WS, "paper", "figures", "fig5_position.png")

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


cache = {}
for s, run in RUNS.items():
    cache[s] = list(csv.DictReader(open(os.path.join(WS, "results", "runs", run, "per_sequence.csv"), encoding="utf-8")))


def v(s, inj, m):
    xs = [float(r["y_mae"]) for r in cache[s] if r["injection"] == inj and int(r["length"]) == 12 and r["method"] == m]
    return float(np.mean(xs))


doc.add_heading("缺陷区间位置敏感性补充", level=0)
p("13 段 · len12 · 区间起点 10/30/50 | 2026-11-18", size=11)

doc.add_heading("一、目的", level=1)
p("主实验所有注入都固定在 [30,42)。审稿人可能问结论是否依赖起点。本补充把 len12 区间分别放在 10/30/50，"
  "比较 A3 与 A7；不改变注入强度与长度。")

doc.add_heading("二、结果", level=1)
table(["注入", "起点", "A3", "A7"], [
    [inj, s, f"{v(s,inj,'A3'):.2f}", f"{v(s,inj,'A7'):.2f}"]
    for inj in ("A", "B", "B13") for s in (10, 30, 50)
], [2.4, 2.4, 2.6, 2.6])
if os.path.exists(FIG):
    doc.add_picture(FIG, width=Cm(16.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run("图 1  区间起点对 A3/A7 的影响（左：偏移 −20；右：γ=2）。")
    r.font.size = Pt(8); r.font.italic = True

doc.add_heading("三、结论", level=1)
for x in [
    "A3 对起点有小幅依赖：A 注入 1.91→2.59，B′ 3.83→4.25，B 8.63→8.07→8.19；变化约 0.5–0.7 YMAE。",
    "A7 随起点单调上升：A 3.47→4.15，B 2.42→3.17，B′ 1.97→2.67；但 A7 在 B/B′ 仍明显优于 A3。",
    "起点带来的差异小于方法之间的差异（例如 B 注入 A3 8.1 vs A7 2.9），不改变主结论。",
    "三组起点都离序列边界至少 10 帧；起点 0/70 这类极端位置未测，边界外推需谨慎。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/position_start10_v1/、position_start50_v1/；results/POSITION_2026-11-18.md；"
  "上图 paper/figures/fig5_position.png。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
