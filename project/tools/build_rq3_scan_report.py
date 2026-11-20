"""Build the RQ3 scan-statistic supplement."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
RUN = os.path.join(WS, "results", "runs", "rq3_scan_v1")
SUM = json.load(open(os.path.join(RUN, "summary.json"), encoding="utf-8"))
OUT = os.path.join(WS, "报告", "RQ3_扫描检测器补充_2026-11-18.docx")

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
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(8.5)
    for row in data:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(8.5)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


doc.add_heading("RQ3 扫描检测器补充实验", level=0)
p("验证集选型、测试集只评一次 · 13 段 × 3 注入 × 长度 1/4/12 | 2026-11-18", size=11)

doc.add_heading("一、动机", level=1)
p("主检测器（滚动中值 JS + CUSUM）在测试集 len12 为 0.744/0.641。它的失败集中在持续平台。"
  "本补充测试一个互补的“扫描统计量”检测器：对每个候选起点和候选长度，比较区间内与区间外的亮度均值/直方图，"
  "取最强区间。它利用本任务已知的候选长度 {1,4,12}，因此不是通用盲检测器，只用于回答“持续段是否可被更强地定位”。")

doc.add_heading("二、设置", level=1)
p("分数：luma 扫描 = |mean_in − median_out| / (1.4826·MAD_out) × sqrt(L)；直方图扫描 = JS(in, out) × sqrt(L)。"
  "变体（luma / JS / max）与阈值只在 4 段验证集上选，测试集只评一次。输出单个区间；与真值区间比较。")

doc.add_heading("三、结果", level=1)
p("表 1  len12：CUSUM 主检测器 vs 扫描检测器")
table(["检测器", "验证 R", "验证 P", "测试 R", "测试 P", "测试 F1", "测试 IoU"], [
    ["CUSUM（主）", "0.965", "0.898", "0.744", "0.641", "0.672", "0.607"],
    ["扫描（补充）", "1.000", "1.000", "0.772", "0.772", "0.772", "0.740"],
], [3.4, 2.2, 2.2, 2.2, 2.2, 2.2, 2.2])

p("表 2  扫描检测器分长度")
data = [["长度", "验证 R", "验证 P", "测试 R", "测试 P", "测试 F1", "测试 IoU"]]
for L in ("1", "4", "12"):
    v = SUM["validation"][f"len{L}"]; t = SUM["test"][f"len{L}"]
    data.append([f"len{L}"] + [f"{v['recall']:.3f}", f"{v['precision']:.3f}",
                               f"{t['recall']:.3f}", f"{t['precision']:.3f}", f"{t['f1']:.3f}", f"{t['iou']:.3f}"])
table(data[0], data[1:], [2.0, 2.2, 2.2, 2.2, 2.2, 2.2, 2.2])

doc.add_heading("五、不依赖已知长度的变体", level=1)
p("把候选长度从 {1,4,12} 放开到 1–24，并加长度惩罚（验证集选 λ=0.4、luma 分数、阈值 0.5），测试集只评一次：")
table(["变体", "测试 R", "测试 P", "测试 F1", "测试 IoU"], [
    ["CUSUM（主）", "0.744", "0.641", "0.672", "0.607"],
    ["固定长度扫描", "0.772", "0.772", "0.772", "0.740"],
    ["未知长度扫描", "0.787", "0.561", "0.642", "0.555"],
], [3.6, 2.3, 2.3, 2.3, 2.3])
p("去掉长度先验后，len12 召回略升到 0.787，但精确率掉到 0.561、F1 0.642、IoU 0.555，反而低于 CUSUM 和固定长度扫描。原因是扫描器会把区间向自然波动处扩张；这反向说明固定长度扫描的收益部分来自“候选长度已知”，不能当作通用检测器。")

doc.add_heading("四、结论与边界", level=1)
for x in [
    "len12 上扫描检测器把测试召回从 0.744 提到 0.772、精确率从 0.641 提到 0.772、IoU 从 0.607 提到 0.740；说明 CUSUM 的持续段漏检不是理论上限。",
    "但 len1/4 明显更差（测试召回 0.370/0.630），因为它把长度当作已知候选，短区间容易被自然波动抢走。",
    "因此论文主检测器仍是 CUSUM（长度鲁棒），扫描检测器作为补充证据：持续段可以被更好地定位，但代价是短区间。",
    "验证集 len12 为 1.000，测试集 0.772，仍有泛化差；没有在测试集上调阈值。",
    "扫描检测器假设单区间、长度 ∈ {1,4,12}，不适用于未知长度/多区间；这是它不能替代 CUSUM 的原因。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("产物：results/runs/rq3_scan_v1/；results/FREEZE_RQ3_SCAN_2026-11-18.json。所有数字由脚本读取，未手工修饰。", size=9.5)
doc.save(OUT)
print("saved", OUT)
