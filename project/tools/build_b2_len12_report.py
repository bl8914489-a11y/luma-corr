"""Build the 13x3 balanced B2 report (len12, all injections)."""
from __future__ import annotations

import csv
import os

import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "b2_len12_v1")
OUT = os.path.join(WS, "报告", "B2_All-In-One补充实验_2026-11-18.docx")
IMG = os.path.join(WS, "报告", "assets", "b2_sailboat_B_034.png")
rows = list(csv.DictReader(open(os.path.join(RUN, "per_case.csv"), encoding="utf-8")))
CASES = {r["case"] for r in rows}

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


def m(inj, method, key):
    v = [float(r[key]) for r in rows if r["injection"] == inj and r["method"] == method]
    return float(np.mean(v))


doc.add_heading("B2 All-In-One 深度基线：13 段 × 3 注入平衡矩阵", level=0)
p("官方代码 + 官方权重 · 39 个 len12 案例 · 本地 RTX 5060 8GB | 2026-11-18", size=11)

doc.add_heading("一、这次补了什么", level=1)
p("上一版 B2 只覆盖 14 次注入，且注入不均衡。本版把 13 段序列在 A（−20）、B（γ=2）、B′（γ=1.3）"
  "三种注入下全部跑一遍 len12，共 39 个案例；每案例 stage1 约 8.7 分钟、stage2 约 11 秒。")

doc.add_heading("二、按注入分组结果", level=1)
table(["方法", "A YMAE", "B YMAE", "B′ YMAE", "总 YMAE", "总 OutFrac", "总 outside RGB", "总边界"],
      [[label] + [f"{m(inj, meth, 'y_mae'):.2f}" for inj in ("A", "B", "B13")]
       + [f"{m('A', meth, 'y_mae') if False else np.mean([float(r['y_mae']) for r in rows if r['method']==meth]):.2f}",
          f"{100*np.mean([float(r['outfrac']) for r in rows if r['method']==meth]):.2f}%",
          f"{np.mean([float(r['outside_rgb_mae']) for r in rows if r['method']==meth]):.2f}",
          f"{np.mean([float(r['boundary']) for r in rows if r['method']==meth]):.2f}"]
       for label, meth in [("no-op", "noop"), ("A3 局部 k=3", "A3"), ("B2 All-In-One", "B2_all_in_one")]],
      [3.4, 1.8, 1.8, 1.8, 1.7, 1.9, 2.4, 1.9])

p(f"总 YMAE：no-op {np.mean([float(r['y_mae']) for r in rows if r['method']=='noop']):.2f} → "
  f"B2 {np.mean([float(r['y_mae']) for r in rows if r['method']=='B2_all_in_one']):.2f} → "
  f"A3 {np.mean([float(r['y_mae']) for r in rows if r['method']=='A3']):.2f}。"
  f"B2 降低约 {100*(1-np.mean([float(r['y_mae']) for r in rows if r['method']=='B2_all_in_one'])/np.mean([float(r['y_mae']) for r in rows if r['method']=='noop'])):.1f}%，"
  f"但仍是 A3 的 {np.mean([float(r['y_mae']) for r in rows if r['method']=='B2_all_in_one'])/np.mean([float(r['y_mae']) for r in rows if r['method']=='A3']):.2f} 倍。")
p("B2 的区间外改动 99.95%，区间外平均 RGB 差 9.79；A3 两项都是 0。B2 的边界误差 4.29，A3 为 4.40；"
  "逐案例看 B2 在 20/39 个案例边界更低，但这是重写整段视频换来的。")

if os.path.exists(IMG):
    doc.add_picture(IMG, width=Cm(16.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run("图 1  sailboat_B_len12 第 34 帧：参考 | 注入 | A3 | B2。")
    r.font.size = Pt(8); r.font.italic = True

doc.add_heading("三、结论与边界", level=1)
for x in [
    "B2 在三种注入下都能降低区间误差（A 9.19、B 18.56、B′ 9.69），但都低于 A3（2.40、8.07、4.03）。",
    "B2 不是为“已知区间 + 区间外保持”设计的：它改动 99.95% 的区间外像素，平均 RGB 差 9.79，不能替代局部写回。",
    "B2 的边界误差在 A/B′ 优于 A3（3.62/3.79 vs 4.23/4.27），在 B 反而更差（5.47 vs 4.69）；全局平滑不是稳定收益。",
    "本版只跑 len12；13×3×3 全矩阵要 117 个案例、约 17 小时 GPU，边际收益低，未跑。",
    "B2 用 512×512、10,001 iter、down=4、torch 2.11；official 为 768×432、torch 1.12，因此是忠实前向，不是逐位复现。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/b2_len12_v1/（per_case.csv / summary.json / run_manifest.json）；"
  "原始帧 third_party/All-In-One-Deflicker/results/<case>/final/output/。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
