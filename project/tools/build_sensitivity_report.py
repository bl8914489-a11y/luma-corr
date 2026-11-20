"""Build the injection-strength sensitivity supplement."""
from __future__ import annotations

import csv
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "sensitivity_v1")
OUT = os.path.join(WS, "报告", "参数敏感性补充_2026-11-18.docx")
FIG = os.path.join(WS, "paper", "figures", "fig4_sensitivity.png")

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


def table(headers, rows, widths):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(9)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(9)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


rows = list(csv.DictReader(open(os.path.join(RUN, "per_sequence.csv"), encoding="utf-8")))


def mean(inj, L, m, key="y_mae"):
    v = [float(r[key]) for r in rows if r["injection"] == inj and int(r["length"]) == L and r["method"] == m]
    return sum(v) / len(v) if v else float("nan")


doc.add_heading("注入强度敏感性补充实验", level=0)
p("13 段序列 · len12 · 偏移 −10/−20/−30、gamma 1.3/1.5/2.0/2.5 | 2026-11-18", size=11)

doc.add_heading("一、目的", level=1)
p("主实验只用了 −20、gamma 2.0、gamma 1.3 三个注入强度。审稿人可能会问结论是否只在单一强度上成立。"
  "本补充在全部 13 段、len12 上扫描 7 个强度，比较 A1/A2/A3/A7，共 1,365 个条件。")

doc.add_heading("二、结果", level=1)
table(["注入", "A1 no-op", "A2 median-7", "A3 linear k=3", "A7 adaptive γ"], [
    [inj, f"{mean(inj,12,'A1'):.2f}", f"{mean(inj,12,'A2'):.2f}", f"{mean(inj,12,'A3'):.2f}", f"{mean(inj,12,'A7'):.2f}"]
    for inj in ["A10", "A20", "A30", "B13", "B15", "B20", "B25"]
], [2.6, 3.2, 3.4, 3.4, 3.4])
if os.path.exists(FIG):
    doc.add_picture(FIG, width=Cm(16.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run("图 1  偏移幅度（左）与 gamma 强度（右）对区间 Y MAE 的影响。")
    r.font.size = Pt(8); r.font.italic = True

doc.add_heading("三、结论", level=1)
for x in [
    "A3 对恒定偏移几乎不敏感：偏移 −10→−30，Y MAE 2.38→2.61，说明加性偏移能在区间内被准确抵消；残差主要来自边界与统计估计，不是偏移本身。",
    "A2 的误差随偏移线性上升（9.61→29.35），因为 7 帧中值窗口在 len12 时被缺陷污染；这与主实验的“局部估计器窗口长度是关键”一致。",
    "gamma 下 A3 随强度上升（4.03→10.73），A7 基本稳定（2.50→3.38）；A7 在 gamma≥1.5 时全面优于 A3。这支持“gamma 残差应归因于加性校正的削波，而不是注入本身”。",
    "A3 的削波比例随 gamma 从 0.80% 升到 2.46%，A7 仅 0.12%→0.71%；与主实验的削波归因一致。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("边界：本补充只跑 len12，不含 1/4 帧；A3 的削波比例是全 13 段区间平均，数值低于主实验 dev-3 的单帧最坏值，两者定义不同，不能直接混用。")

doc.add_heading("四、产物", level=1)
for x in [
    "运行：results/runs/sensitivity_v1/（per_sequence.csv / per_frame.csv / summary.json）",
    "汇总：results/SENSITIVITY_2026-11-18.md",
    "图：paper/figures/fig4_sensitivity.png",
]:
    doc.add_paragraph(x, style="List Bullet")
doc.save(OUT)
print("saved", OUT)
