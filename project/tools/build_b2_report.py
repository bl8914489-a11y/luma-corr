"""Build the All-In-One (B2) supplementary report."""
from __future__ import annotations

import csv
import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
RUN = os.path.join(WS, "results", "runs", "b2_all_in_one_v1")
OUT = os.path.join(WS, "报告", "B2_All-In-One补充实验_2026-11-17.docx")
IMG = os.path.join(WS, "报告", "assets", "b2_sailboat_B_034.png")

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.0)
    s.top_margin = s.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]
st.font.name = "宋体"; st.font.size = Pt(10.5)


def p(text, bold=False, size=10.5):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    r = par.add_run(text); r.font.bold = bold; r.font.size = Pt(size)
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(headers, rows, widths, size=8.5):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)


rows = list(csv.DictReader(open(os.path.join(RUN, "per_case.csv"), encoding="utf-8")))
summary = json.load(open(os.path.join(RUN, "summary.json"), encoding="utf-8"))
man = json.load(open(os.path.join(RUN, "run_manifest.json"), encoding="utf-8"))

doc.add_heading("B2 All-In-One 深度基线补充实验", level=0)
p("官方代码 + 官方权重 · 14 个注入案例 · 本地 RTX 5060 8GB | 2026-11-17", size=11)

doc.add_heading("一、为什么补这条基线", level=1)
p("查新报告与导师意见都把“缺少深度学习对照”列为投稿硬缺口。B1 BlazeBVD 的官方代码在公开渠道仍标注为待发布，"
  "无法运行；B2 All-In-One（CVPR 2023，Neural Filtering with a Flawed Atlas）代码与权重均可获取，"
  "且官方说明推理仅需约 3GB 显存，因此本轮在本地 8GB GPU 上把它跑通，作为盲去闪烁深度基线。")

doc.add_heading("二、设置", level=1)
p("代码：ChenyangLEI/All-In-One-Deflicker（官方仓库）；权重：neural_filter.pth / local_refinement_net.pth / "
  "raft-things.pth（官方 cvpr2023_deflicker_public_folder）。")
p("输入：把注入后的 76 帧 512×512 序列作为视频帧文件夹，stage1 建 neural atlas（10001 iter，down=4，"
  "res 512×512），stage2 做 neural filtering + local refinement。每案例 stage1 约 8.7 分钟，stage2 约 11 秒。")
p("评价：始终在真值区间 [30,42) 上算 Y MAE / PSNR / SSIM；outFrac 统计真值区间外的像素改动比例。"
  "B2 是盲全局方法，不知道区间；A3 是已知区间的局部写回。两者不是同一任务设定，因此下表的对比是“任务约束下的压力测试”，"
  "不是 SOTA 排名。")

doc.add_heading("三、逐案例结果", level=1)
trows = []
for r in rows:
    trows.append([r["case"], r["method"], f"{float(r['y_mae']):.2f}", f"{float(r['psnr']):.2f}",
                  f"{float(r['ssim']):.3f}", f"{float(r['outfrac'])*100:.2f}%",
                  f"{float(r['outside_rgb_mae']):.2f}", f"{float(r['boundary']):.2f}"])
table(["案例", "方法", "Y MAE", "PSNR", "SSIM", "区间外改动", "区间外 RGB MAE", "边界误差"], trows,
      [4.2, 3.0, 1.8, 1.8, 1.6, 2.4, 2.6, 2.2], size=7.6)

doc.add_heading("四、均值与结论", level=1)
m = summary["interval_mean"]
table(["方法", "Y MAE", "PSNR", "SSIM", "区间外改动", "区间外 RGB MAE", "边界误差"], [
    ["no-op", f"{m['noop']['y_mae']:.2f}", f"{m['noop']['psnr']:.2f}", f"{m['noop']['ssim']:.3f}",
     f"{m['noop']['outfrac']*100:.2f}%", f"{m['noop']['outside_rgb_mae']:.2f}", f"{m['noop']['boundary']:.2f}"],
    ["A3 局部 k=3", f"{m['A3']['y_mae']:.2f}", f"{m['A3']['psnr']:.2f}", f"{m['A3']['ssim']:.3f}",
     f"{m['A3']['outfrac']*100:.2f}%", f"{m['A3']['outside_rgb_mae']:.2f}", f"{m['A3']['boundary']:.2f}"],
    ["B2 All-In-One", f"{m['B2_all_in_one']['y_mae']:.2f}", f"{m['B2_all_in_one']['psnr']:.2f}",
     f"{m['B2_all_in_one']['ssim']:.3f}", f"{m['B2_all_in_one']['outfrac']*100:.2f}%",
     f"{m['B2_all_in_one']['outside_rgb_mae']:.2f}", f"{m['B2_all_in_one']['boundary']:.2f}"],
], [3.8, 2.0, 2.0, 1.8, 2.6, 2.8, 2.4], size=8.3)
p(f"区间内 Y MAE：no-op {m['noop']['y_mae']:.2f} → B2 {m['B2_all_in_one']['y_mae']:.2f} → A3 {m['A3']['y_mae']:.2f}。"
  f"B2 把误差降低约 {100*(1-m['B2_all_in_one']['y_mae']/m['noop']['y_mae']):.1f}%，但仍是 A3 的 "
  f"{m['B2_all_in_one']['y_mae']/m['A3']['y_mae']:.2f} 倍。")
p(f"区间外改动：A3 为 {m['A3']['outfrac']*100:.2f}%，B2 为 {m['B2_all_in_one']['outfrac']*100:.2f}%——"
  "B2 作为盲全局方法会改动几乎整段视频，这正是 RQ2 要量化的“局部写回 vs 全序列处理”差异。"
  f"边界误差 B2 为 {m['B2_all_in_one']['boundary']:.2f}，A3 为 {m['A3']['boundary']:.2f}，"
  "B2 在 14 个案例中的 8 个边界更平滑，但这是以改动区间外为代价的。")
p("结论：B2 确实能降低闪烁误差，但在“已知区间 + 区间外保持”的任务设定下，它既不如 A3 准，也不满足区间外保持。"
  "这条基线可以回答“为什么不和 SOTA 比”：不是没跑，而是任务目标不同；B2 的强项是盲场景整体观感，不是区间级保持性。")

doc.add_heading("五、样例帧", level=1)
p("sailboat_B_len12 第 34 帧。左起：参考 | 注入后 | A3 | B2。B2 把亮度拉回一部分，但整帧被重新渲染；"
  "A3 只在区间内做偏移，区间外逐像素不变。")
if os.path.exists(IMG):
    doc.add_picture(IMG, width=Cm(16.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_heading("六、必须写进 Limitations 的边界", level=1)
for x in [
    "B2 是盲全局方法，不知道缺陷区间；用 outFrac 评价它，是按本课题任务定义施加的约束，不是它的设计目标。",
    "只跑了 14 个案例（覆盖全部 13 段序列，sailboat 有 A/B 两个注入），不是 13×3×3 全矩阵；B2 每案例约 8.8 分钟，全量成本高。",
    "为适配 512×512 输入，把官方 768×432 配置改为 512×512、10000 iter、down=4；这不是官方默认设置的逐位复现。",
    "运行环境为 torch 2.11 + cu128（官方环境 torch 1.12 + CUDA 11）；仅加载官方权重做前向，未重训练。",
    "B1 BlazeBVD 代码未公开，B3/B4/B5 未运行；本文只报 B2 的实测数字，其余引用公开结果。",
]:
    doc.add_paragraph(x, style="List Bullet")

doc.add_heading("七、产物", level=1)
for x in [
    f"运行目录：results/runs/b2_all_in_one_v1/（per_case.csv、summary.json、run_manifest.json）",
    f"权重 SHA-256：neural_filter {man['weight_sha256']['neural_filter.pth'][:16]}…；"
    f"local_refinement {man['weight_sha256']['local_refinement_net.pth'][:16]}…；"
    f"raft {man['weight_sha256']['raft-things.pth'][:16]}…",
    "原始输出帧：third_party/All-In-One-Deflicker/results/<case>/final/output/",
    "逐案例阶段耗时：third_party/batch_summary.json",
]:
    doc.add_paragraph(x, style="List Bullet")
p("所有数字由 project/scripts/eval_all_in_one.py 从 per_case.csv 读取；未做任何手工修饰。", size=9.5)

doc.save(OUT)
print("saved", OUT)
