"""Build the journal-feasibility assessment DOCX."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "报告", "期刊发表可行性评估_2026-11-21.docx")


_DOC = None


def p(text, bold=False, size=10.5):
    par = _DOC.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(doc, headers, rows, widths=None, size=8.5):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for i, x in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(str(x)); r.font.bold = True; r.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(x)); r.font.size = Pt(size)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()


doc = Document(); _DOC = doc
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(1.9)
st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

doc.add_heading("期刊发表可行性评估", level=0)
p("四条限制下能否投 SIVP（JCR Q3）| 2026-11-21", size=11)

p("直接结论：以现在这四条限制，可以支持“投 SIVP 并进入外审”，但不能支持“保证录用”。"
  "按 SIVP 的标准，这是一篇 borderline 的实证/复现型稿件：实验和复现很强，创新和真实场景证据偏弱。"
  "审稿人大概率给 major revision，而不是直接接收；如果包装成“新方法/新 SOTA”，被拒风险更高。", bold=True)

doc.add_heading("1  四条限制分别有多致命", level=1)
table(doc, ["限制", "对投稿的影响", "是否致命"], [
    ["自然视频没有校正精度", "论文主 claims 是合成受控实验；自然只做检测、不做校正，作为 limitations 可接受", "不致命，但限制“应用价值”"],
    ["RQ3 只有 0.744", "已如实写成泛化差距；但占篇幅大、结论负，容易把论文重心拉偏", "不致命，建议压缩"],
    ["B2 只有一个学习型基线", "作为“可获取的官方基线”可接受；不能声称 SOTA", "不致命，但会被要求补基线"],
    ["单标注、无 kappa", "自然部分只是 preliminary；不冒充双人一致性即可", "不致命，但自然证据弱"],
], [4.0, 8.5, 3.5])
p("这四条都不是“数据造假/无法复现”级别的问题，而是 claim 的边界问题。只要论文不超出这些边界，"
  "它们可以写进 limitations，而不是硬伤。")

doc.add_heading("2  现在能支撑什么、不能支撑什么", level=1)
p("能支撑：", bold=True)
for x in [
    "已知区间局部校正的受控实证；",
    "全 13 段、1,170 条件、208 个 B2 案例；",
    "局部 vs 全局写回、削波归因；",
    "检测误差传导（端到端 1.4–3.0 倍放大）；",
    "CPU 成本与工程选型建议；",
    "可复现包（575/575 哈希一致）。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("不能支撑：", bold=True)
for x in [
    "“真实自然视频校正有效”的结论；",
    "“检测器达到 0.90/可实际部署”的结论；",
    "“B2 被全面超越/我们是 SOTA”的结论；",
    "双人标注一致性。",
]:
    doc.add_paragraph(x, style="List Bullet")

doc.add_heading("3  SIVP 的匹配与风险", level=1)
table(doc, ["维度", "评估", "说明"], [
    ["Scope 匹配", "高", "SIVP 收应用型/实践型视频处理，受控基准和复现研究在范围内"],
    ["创新性", "弱到中", "没有新网络；局部写回不改区间外接近定义；价值在误差传导、成本、选型、复现"],
    ["证据量", "够 Q3", "1,170 条件 + 208 个 B2 案例 + 多区间，比一般 Q3 实证稿扎实"],
    ["真实场景", "弱", "只有检测、无校正精度；应用型期刊会追问“真实缺陷能不能校正”"],
    ["形式合规", "未完成", "作者/Statements/关键词/Fig3/参考文献/LaTeX 均未按 SIVP 要求补齐"],
], [3.0, 2.6, 10.0])
p("所以：可以送外审，但不能保证过；属于“可投的 Q3 尝试”，不是“稳发的成果”。")

doc.add_heading("4  两条路", level=1)
doc.add_heading("路线 A：12/02 前投出去（现实）", level=2)
p("适合时间紧、先要一次投稿记录。")
for x in [
    "把 RQ3 从主贡献降为“边界分析”，压缩到一小节或 Supplementary；",
    "自然标注只放 limitations，不放主结果；",
    "主表用全 13 段（已做）；",
    "补 P0 形式项：作者/单位、Statements、关键词 5 个、Fig3 重出、参考文献卷期页；",
    "定位写成“controlled empirical + reproducibility + practical selection”，不要写新方法。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("预期：能过编辑部初筛，外审 major revision 概率高；接收不确定。")

doc.add_heading("路线 B：推迟 1–2 周，把 P1-2 补上（更稳）", level=2)
p("不用伪造 YMAE，可以做无参考的自然校正实验：")
for x in [
    "对 10–20 个自然片段，用人工区间做 A3/A5/A7 校正；",
    "评“校正前后时序闪烁指标”（帧间 luma 差、直方图 JS）和区间外改动；",
    "不做 YMAE，只报告“闪烁下降 + 区间外保持”；",
    "再加一个轻量学习型基线，或把 B2 的检测+局部校正串联。",
]:
    doc.add_paragraph(x, style="List Bullet")
p("这不能替代干净参考，但能回答“真实缺陷校正后是否更稳”，比现在只有检测强很多。"
  "这条路会让 Q3 的接收概率明显提高，但 12/02 会很紧。")

doc.add_heading("5  建议", level=1)
table(doc, ["你的目标", "建议", "风险"], [
    ["12/02 硬截止，先投出去", "走 A：投 SIVP，按边界性研究写，不承诺真实场景", "major revision 概率高；可能被拒"],
    ["目标是“发出来”，不赶截止", "走 B：补无参考自然校正 + 第二基线，推迟一轮", "多花 1–2 周；接收概率更高"],
], [5.0, 7.5, 4.0])
p("以现在的内容，支持你投 SIVP，但不支持你对外说“这个成果可以稳发 Q3”。"
  "审稿人最可能拒的理由不是数据假，而是：没有新方法、真实场景证据不足、检测没解决。这三条目前都还在。")

doc.add_heading("6  即使走 A，也必须先补的 P0", level=1)
for x in [
    "作者规范姓名、单位、通讯作者、邮箱、ORCID；",
    "Statements and Declarations：Funding / Competing Interests / Ethics / Consent / Data / Authorship / AI；",
    "关键词从 7 个减到 5 个；",
    "Fig3 重出（≥300 dpi 半调，四面板可辨），统一 Fig1/2/3 命名；",
    "参考文献补卷期页、DOI 全链接，清理未引用条目；",
    "修掉公式残留（\\,、_hat、\\1,4,12\\ 等），关键定义编号；",
    "主表改全 13 段（已完成），开发集放 Supplementary；",
    "文档内陈旧数字统一（34→37、99.96→99.95、文件数/包大小）。",
]:
    doc.add_paragraph(x, style="List Bullet")

doc.add_heading("7  一页结论", level=1)
p("这四条限制不构成“不能投”，但构成“不能保证发”。当前成果足以支撑一次诚实的 Q3 实证/复现投稿；"
  "如果审稿人按方法创新或真实场景标准要求，现稿会吃力。")
p("我的判断：投 SIVP 是合理的，但请按“边界性研究”写，不要按“新方法”写；"
  "如果 12/02 不是硬截止，优先补无参考自然校正，再投。")

doc.save(OUT)
print("saved", OUT)
