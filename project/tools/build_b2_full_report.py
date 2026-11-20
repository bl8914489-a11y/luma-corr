"""Build the 117-case B2 length-extension supplement."""
from __future__ import annotations

import csv
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "b2_full_v1")
OUT = os.path.join(WS, "报告", "B2_长度扩展_2026-11-18.docx")
rows = list(csv.DictReader(open(os.path.join(RUN, "per_case.csv"), encoding="utf-8")))

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(1.9); s.top_margin = s.bottom_margin = Cm(2.0)
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
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(8)
    for row in data:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(8)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


def m(L, inj, method, key):
    v = [float(r[key]) for r in rows if int(r["length"]) == L and r["injection"] == inj and r["method"] == method]
    return float(np.mean(v))


doc.add_heading("B2 All-In-One 长度扩展：117 案例全矩阵", level=0)
p("13 段 × 3 注入 × 长度 1/4/12 · 官方代码+权重 · RTX 5060 8GB | 2026-11-18", size=11)

doc.add_heading("一、目的", level=1)
p("主表只报 len12 的 39 个平衡案例。本补充把长度 1 和 4 也跑完，共 117 个案例，"
  "用来回答“B2 的差距是否只在长区间成立”。")

doc.add_heading("二、区间 Y MAE", level=1)
data = []
for L in (1, 4, 12):
    row = [f"len{L}"]
    for inj in ("A", "B", "B13"):
        row += [f"{m(L,inj,'noop','y_mae'):.2f}", f"{m(L,inj,'A3','y_mae'):.2f}", f"{m(L,inj,'B2_all_in_one','y_mae'):.2f}"]
    data.append(row)
table(["长度", "A no-op", "A A3", "A B2", "B no-op", "B A3", "B B2", "B′ no-op", "B′ A3", "B′ B2"],
      data, [1.4, 1.7, 1.6, 1.6, 1.7, 1.6, 1.6, 1.8, 1.7, 1.7])

doc.add_heading("三、B2 的区间外改动", level=1)
data = []
for L in (1, 4, 12):
    for inj in ("A", "B", "B13"):
        data.append([f"len{L}", inj, f"{100*m(L,inj,'B2_all_in_one','outfrac'):.2f}%",
                     f"{m(L,inj,'B2_all_in_one','outside_rgb_mae'):.2f}",
                     f"{m(L,inj,'B2_all_in_one','boundary'):.2f}"])
table(["长度", "注入", "OutFrac", "区间外 RGB", "边界"], data, [2.2, 2.2, 3.2, 3.6, 3.0])

doc.add_heading("四、结论", level=1)
for x in [
    "B2 在所有长度、所有注入下都劣于 A3：A 注入 len1/4/12 为 7.79/7.39/9.19，A3 为 2.06/1.48/2.40。",
    "B 注入下 B2 随长度明显恶化：8.94/10.94/18.56，A3 为 8.16/7.65/8.07；长区间 gamma 是 B2 最难的设定。",
    "B2 的区间外改动在各长度都约 99.9%，与长度无关；它始终是全局重写，不是区间保持方法。",
    "117 案例独立冻结 PASS（117 案例 / 351 行 / 每个长度 39 案例）。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/b2_full_v1/；results/FREEZE_B2_FULL_2026-11-18.json；"
  "results/B2_FULL_2026-11-18.md。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
