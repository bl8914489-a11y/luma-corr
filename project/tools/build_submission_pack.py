"""Build the submission pack: cover letter, checklist, and anticipated-review notes."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "投稿")
os.makedirs(OUT, exist_ok=True)


def p(doc, text, bold=False, size=10.5):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(5)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def cover():
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.4); s.top_margin = s.bottom_margin = Cm(2.2)
    p(doc, "Cover Letter", bold=True, size=14)
    p(doc, "To the Editor-in-Chief")
    p(doc, "Signal, Image and Video Processing (Springer)")
    p(doc, "November 17, 2026")
    p(doc, "Dear Editor,")
    p(doc, "We submit the manuscript entitled \u201cLocal Brightness Correction for Known Defect "
           "Intervals in Generated Video: A Reproducible Empirical Study\u201d for consideration in "
           "Signal, Image and Video Processing.")
    p(doc, "Blind video deflickering methods are usually evaluated on whole videos and are not asked "
           "to preserve frames outside a defect interval. In editing, repair and quality-control "
           "pipelines the interval is often known, and the practical question is different: how "
           "accurately can a deterministic estimator restore that interval, and how far does the "
           "correction leak outside it? The manuscript treats this question as a controlled "
           "experimental variable rather than proposing another end-to-end network.")
    p(doc, "The study makes four concrete contributions. First, it provides a reproducible benchmark "
           "of 13 sequences, 1,170 measured conditions, ten deterministic correctors and three "
           "controlled injections, with frame-level hashes, configuration hashes and a one-click "
           "reproduction package. Second, it separates interval error, outside preservation and "
           "boundary error, and shows that the same median estimator changes 33.2% of outside pixels "
           "when write-back is global but none when it is local. Third, it attributes the gamma "
           "residual of the additive-offset family to correction-side clipping (4.53%/5.38%/3.43% on "
           "three sequences) and shows that gamma-aware baselines remove most of it. Fourth, it "
           "re-implements BlazeBVD Eq. (5), explains why its local-mean rule misses sustained "
           "plateaus, and reports a pre-registered held-out recall of 0.744 rather than an optimistic "
           "all-sequence number.")
    p(doc, "We also run the official All-In-One model on thirty-nine injected cases as a deep blind baseline. "
           "It reduces interval error by 60.4% but changes 99.95% of outside pixels, which makes the "
           "task difference explicit. We do not present this as a state-of-the-art ranking; the "
           "manuscript is positioned as an empirical and reproducibility contribution, and its "
           "limitations (13 sequences, synthetic injections, detector recall below target, B1 not "
           "runnable because its code is not public) are stated in the paper.")
    p(doc, "We believe the work fits the journal\u2019s interest in experimentally rigorous image and "
           "video processing. All configurations, run manifests, per-frame hashes, result tables and "
           "the reproduction package are available; the manuscript contains no fabricated or "
           "hand-adjusted numbers, and every headline value passes an automated freeze check.")
    p(doc, "The manuscript is original, has not been published elsewhere, and is not under "
           "consideration by another journal. All authors have approved the submission and declare "
           "no competing interests. The data are derived from the public Blind-Video-Deflickering-"
           "Dataset (CC BY 4.0); the All-In-One code and weights are used under their official "
           "release and are not redistributed.")
    p(doc, "Thank you for your consideration.")
    p(doc, "Sincerely,")
    p(doc, "ZHIKUN (50260258)")
    p(doc, "Affiliation and corresponding author details: to be completed")
    p(doc, "Email: to be completed")
    doc.save(os.path.join(OUT, "Cover_Letter_2026-11-17.docx"))


def checklist():
    wb = Workbook(); ws = wb.active; ws.title = "投稿清单"
    ws.append(["类别", "项目", "状态", "证据/文件", "负责人", "截止"])
    rows = [
        ("稿件", "正文 DOCX（13 页、5 表、3 图、41 条引用）", "完成", "paper/manuscript_draft_2026-11-17.docx", "ZHIKUN", "11/25"),
        ("稿件", "作者、单位、通讯作者、基金", "待补", "manuscript 首页", "ZHIKUN", "11/24"),
        ("稿件", "关键词与摘要定稿", "完成", "manuscript", "ZHIKUN", "11/25"),
        ("稿件", "参考文献格式改为期刊样式", "待做", "references.bib / 正文", "ZHIKUN", "11/27"),
        ("图表", "Figure 1 写回范围", "完成", "paper/figures/fig3_writeback_scope.png", "ZHIKUN", "11/24"),
        ("图表", "Figure 2 检测分数", "完成", "paper/figures/fig2_detection_scores.png", "ZHIKUN", "11/24"),
        ("图表", "Figure 3 B2 样例", "完成", "报告/assets/b2_sailboat_B_034.png", "ZHIKUN", "11/24"),
        ("图表", "表格 1–5 与正文数字一致", "完成", "FREEZE_2026-11-17.json（37/37 PASS）", "ZHIKUN", "11/24"),
        ("数据", "数据来源、许可、SHA-256", "完成", "README / 复现包", "ZHIKUN", "11/24"),
        ("代码", "复现包与一键测试", "完成", "交付/复现包_2026-11-17.zip", "ZHIKUN", "11/24"),
        ("声明", "利益冲突、作者贡献、伦理", "待做", "投稿系统", "ZHIKUN", "11/28"),
        ("语言", "英文润色/母语校对", "待做", "manuscript", "ZHIKUN", "11/29"),
        ("投稿", "Cover letter", "完成", "投稿/Cover_Letter_2026-11-17.docx", "ZHIKUN", "11/25"),
        ("投稿", "期刊模板排版（Springer）", "待做", "SIVP 模板", "ZHIKUN", "11/29"),
        ("投稿", "查重/相似度", "待做", "manuscript", "ZHIKUN", "11/29"),
        ("投稿", "上传系统并核对 PDF", "待做", "投稿系统", "ZHIKUN", "12/02"),
    ]
    for r in rows:
        ws.append(list(r))
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F5597")
    widths = [10, 44, 10, 44, 12, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"

    ws2 = wb.create_sheet("预设审稿问题")
    ws2.append(["审稿人可能的问题", "已准备的回答", "证据"])
    qa = [
        ("只有 13 段视频，样本太小", "公开子集只有 13 段（VideoDM/Meta 全部）；逐帧配对与视频级聚类，承认外部效度限制", "Table 1–3, Limitations"),
        ("为什么没有和 SOTA 比", "B2 All-In-One 已用官方权重跑 39 案例（13 段×3 注入）；B1 代码未公开，B3–B5 无权重；任务是已知区间保持，不是盲去闪烁排名", "Table 4, B2 报告"),
        ("检测召回只有 0.744", "预注册测试集如实报告；全 13 段 0.825 只作上限；未在测试集调参", "Table 3, 4.5 节"),
        ("合成注入不真实", "受控注入是为了可归因；真实 T2V 标注因公开数据缺模型/提示词未完成，已写入 limitations", "3.2 节, 5.4 节"),
        ("A3 不是最优（A7 更好）", "论文明确写 A3 不是普适最优；A7 在 gamma 注入 13/13 胜出，p=2.4e-4", "Table 1, 4.2 节"),
        ("k=3 是否拍脑袋", "k=1 往往更好；论文把 k=3 作为原项目方法做可比性，并报告负结果", "Table 5, 4.7 节"),
        ("B2 outFrac≈100% 是否夸张", "B2 是盲全局方法，改动全视频；outFrac 是任务约束下的度量，不是它的设计目标", "Table 4, 5.3 节"),
        ("复现性如何保证", "config/code/frame SHA、独立 validator、37 项冻结检查、一键包", "4.9 节, FREEZE json"),
    ]
    for r in qa:
        ws2.append(list(r))
    for c in ws2[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F5597")
    for i, w in enumerate([34, 70, 26], 1):
        ws2.column_dimensions[chr(64 + i)].width = w
    for row in ws2.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(os.path.join(OUT, "投稿检查清单_2026-11-17.xlsx"))


if __name__ == "__main__":
    cover(); checklist()
    print("saved", OUT)
