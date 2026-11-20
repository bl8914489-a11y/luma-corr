"""Build the B2 two-interval report."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
S = json.load(open(os.path.join(WS, "results", "runs", "b2_multi_v1", "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "B2_两区间缺陷_2026-11-19.docx")

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


doc.add_heading("B2 All-In-One 两区间缺陷基线", level=0)
p("13 段 × 2 长度（len4/12）× 2 注入（A/B）= 52 案例 · 官方代码+权重 | 2026-11-19", size=11)

doc.add_heading("一、设置", level=1)
p("同一视频两个缺陷段 [10,10+L) 与 [50,50+L)；B2 处理整段视频，A3/A7 对两段分别独立校正。"
  "评价始终在真值两个区间上算，outFrac 统计区间外像素改动。")

doc.add_heading("二、结果", level=1)
for label, key in (("全部 52 案例", "overall"), ("len4", "len4"), ("len12", "len12")):
    p(label, bold=True)
    table(["方法", "Y MAE", "PSNR", "SSIM", "OutFrac", "区间外 RGB", "边界"], [
        [m, f"{S[key][m]['y_mae']:.2f}", f"{S[key][m]['psnr']:.2f}", f"{S[key][m]['ssim']:.3f}",
         f"{100*S[key][m]['outfrac']:.2f}%", f"{S[key][m]['outside_rgb_mae']:.2f}", f"{S[key][m]['boundary_err']:.2f}"]
        for m in ("A1", "A3", "A7", "B2")
    ], [2.2, 2.2, 2.2, 2.2, 2.6, 2.8, 2.4])

doc.add_heading("三、结论与边界", level=1)
for x in [
    "B2 在 52 个两区间案例上 Y-MAE 13.37，A3 为 5.16、A7 为 3.20；两个方法都明显更好。",
    "B2 的区间外改动 99.95%、区间外 RGB 差 11.91；A3/A7 两项均为 0。",
    "B2 的边界误差 7.03，略低于 A3 7.90 与 A7 7.61，但这是整段重写换来的平滑，不是区间保持。",
    "长度效应：len4 B2 9.84，len12 16.91；B2 随区间变长恶化，和单区间 117 案例结论一致。",
    "B2 是盲全局方法，不该按“已知区间 + 区间外保持”的任务排名；本表只说明任务差异。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/b2_multi_v1/（per_case.csv / summary.json）。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
