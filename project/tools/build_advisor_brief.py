"""Build the advisor review brief (Chinese, 4-6 pages) with the frozen results."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "报告", "导师汇报_2026-11-18.docx")
B2 = os.path.join(WS, "results", "runs", "b2_all_in_one_v1", "summary.json")
FREEZE = os.path.join(WS, "results", "FREEZE_2026-11-17.json")


def p(doc, text, bold=False, size=10.5):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(doc, headers, rows, widths):
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


def img(doc, path, width=16.0, caption=""):
    if not os.path.exists(path):
        return
    doc.add_picture(path, width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(caption); r.font.size = Pt(8); r.font.italic = True


def main():
    b2 = json.load(open(B2, encoding="utf-8"))["interval_mean"]
    fr = json.load(open(FREEZE, encoding="utf-8"))
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.0)
        s.top_margin = s.bottom_margin = Cm(1.9)
    st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

    doc.add_heading("阶段性成果与投稿决策汇报", level=0)
    p(doc, "2026-11-18 · 数据、实验、初稿与复现包已冻结；请导师定三件事", size=10)

    doc.add_heading("一、一页结论", level=1)
    for x in [
        "实验已跑完：Tier A 1,170 条件、RQ3 1,300 条件、测试集端到端 81 条件、B2 深度基线 39 案例（覆盖全部 13 段）。",
        f"核心数字已冻结：37/37 项检查 PASS；论文初稿 13 页、5 表、3 图、41 条引用。",
        "RQ3 测试集召回 0.744、精确率 0.641，低于 0.90 目标；论文按“边界性发现 + 误差传导”写，不主张新检测器。",
        "B2 官方 All-In-One 已跑通：区间 YMAE 12.48 vs A3 4.84，但区间外改动 99.95%、RGB 差 9.94；盲全局方法不能替代局部写回。",
        "复现包 约 440 文件 / 约 47 MB，包内一键测试通过；远程 GPU 未开启，费用约 ¥0.20。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    doc.add_heading("二、关键数字（全部通过冻结）", level=1)
    table(doc, ["模块", "数字", "含义"], [
        ["Tier A（dev-3）", "A1 19.91 → A3 1.03 / 0.73 / 0.76", "A 注入，len 1/4/12，Y MAE"],
        ["Tier A（dev-3）", "A3 8.65 / 7.87 / 7.89（B）；3.78 / 3.01 / 3.18（B′）", "gamma 注入仍有余差"],
        ["削波", "4.53% / 5.38% / 3.43%", "sailboat / book / horse，B len1"],
        ["RQ2", "A4 区间外改动 33.2%，A3 0%", "局部 vs 全局写回"],
        ["RQ3 全 13 段", "0.825 / 0.737 / 0.690", "len12 召回 / 精确率 / IoU"],
        ["RQ3 测试集", "0.744 / 0.641", "预注册 9 段，未调阈值"],
        ["端到端测试集", "65.5% / 4.01% / 45.7%", "YMAE 降幅 / 区间外改动 / 命中"],
        ["B2（39 案例）", "12.48 / 99.95% / 9.94", "YMAE / 区间外改动 / RGB 差"],
    ], [4.0, 7.6, 5.0])

    doc.add_page_break()
    doc.add_heading("三、三张核心图", level=1)
    img(doc, os.path.join(WS, "报告", "assets", "b2_sailboat_B_034.png"), 15.8,
        "图 1  B2 与 A3 的同帧对比：A3 只改区间，B2 重绘整帧。")
    img(doc, os.path.join(WS, "paper", "figures", "fig2_detection_scores.png"), 15.8,
        "图 2  Eq.(5) 在 knight A 上升高但被 local-mean 阈值压住（0/12）；CUSUM 覆盖 12/12。")
    img(doc, os.path.join(WS, "paper", "figures", "fig3_writeback_scope.png"), 15.8,
        "图 3  A2/A3 区间外 0%，A4 为 33.2%；A4 边界误差接近 A2 而非 A3。")

    doc.add_heading("四、请导师决定的三件事", level=1)
    table(doc, ["决策", "选项", "我的建议"], [
        ["RQ3 定位", "A. 接受 0.744，写成边界性发现；B. 换检测器再冲 0.90", "A。再调阈值就是测试集调参；换方法需 1–2 周且不一定过。"],
        ["B2 是否跑全矩阵", "A. 停在 39 案例；B. 跑 13×3×3=117 案例", "A。39 案例已覆盖 13 段，全矩阵约 17 小时 GPU，边际收益低。"],
        ["真实 T2V 标注", "A. 不做，写入 limitations；B. 找 2 位标注者补 100 段", "A 或 B 取决于 11/22 前能否找到人；公开数据缺模型/提示词，标注成本高。"],
    ], [3.4, 7.6, 5.6])

    doc.add_heading("五、风险与时间表", level=1)
    table(doc, ["日期", "事项", "状态"], [
        ["11/18", "数字冻结 + 复现包 + 导师审阅包", "完成"],
        ["11/20", "GPU 决策（B2 已本地跑通，无需远程）", "完成"],
        ["11/22", "人工标注决策", "待导师定"],
        ["11/25", "导师修改稿", "待启动"],
        ["11/29", "内容冻结 + 语言润色", "待做"],
        ["12/02", "SIVP 投稿", "目标"],
    ], [2.6, 10.4, 3.6])
    p(doc, "主要风险：RQ3 测试集召回不足（已如实写）；B1/B3–B5 未运行（代码/权重不可得）；真实标注缺失（写入 limitations）；本机无 LaTeX，排版需在投稿前完成。")

    doc.add_heading("六、交付物位置", level=1)
    for x in [
        "论文初稿：paper/manuscript_draft_2026-11-17.docx（13 页、5 表、3 图）",
        "B2 补充：报告/B2_All-In-One补充实验_2026-11-17.docx（39 案例）",
        "RQ3 补充：报告/RQ3_D1D2补充实验_2026-11-17.docx",
        "复现包：交付/复现包_2026-11-17.zip（约 440 文件 / 约 47 MB）",
        "数字冻结：results/FREEZE_2026-11-17.json（37/37 PASS）",
        "Cover letter 与检查清单：投稿/",
    ]:
        doc.add_paragraph(x, style="List Bullet")
    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
