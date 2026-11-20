"""Build the minimal-compliance execution checklist for the narrowed manuscript."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "投稿", "最小合规执行清单_2026-11-21.docx")
_DOC = None


def p(text, bold=False, size=10.5):
    par = _DOC.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(headers, rows, widths=None, size=8):
    t = _DOC.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
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
    _DOC.add_paragraph()


doc = Document(); _DOC = doc
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(1.9)
st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

doc.add_heading("最小合规执行清单（SIVP）", level=0)
p("收窄版 manuscript_v2 + Supplementary_v2 | 2026-11-21", size=11)
p("按《最小合规投稿方案》执行：删除 RQ3 主章节、自然标注、端到端；正文保留 3 条主张、4 表 2 图；补 Statements、关键词和声明。"
  "本清单只记录状态，不替代期刊官网核对。")

doc.add_heading("1  已完成", level=1)
table(["项", "状态", "证据"], [
    ["标题/摘要", "完成", "新标题；摘要 214 词；关键词 5 个"],
    ["正文收窄", "完成", "RQ3 主章节、自然标注、端到端移入 SI；正文约 4,800 词"],
    ["主表全 13 段", "完成", "Table 1 改为 13 段；7 个代表方法；完整 10 方法在 SI S1"],
    ["表数/图数", "完成", "4 张表、2 张图"],
    ["Table 3 B2", "完成", "原 Table 4 改为 Table 3；39 案例"],
    ["Statements", "已完成模板", "七项齐全，作者/基金/数据链接为占位"],
    ["SI", "完成", "RQ3、自然标注、端到端、多区间、复现（3 页）"],
    ["Fig2", "完成", "2048×2224、300 dpi、2×2、Fig2 命名"],
    ["复现包", "完成", "575 文件；575/575 哈希；测试不再改写冻结"],
    ["冻结", "完成", "37/37 PASS；E2E 624 行、full13 90 行独立冻结"],
], [3.0, 2.4, 10.5])

doc.add_heading("2  仍缺/阻塞（不补不能投）", level=1)
table(["编号", "项", "现状", "谁来做"], [
    ["A1", "作者、单位、通讯作者、邮箱、ORCID", "占位符", "你/导师"],
    ["A2", "Statements 七项", "模板已写，Funding/Contributions 需填", "你确认"],
    ["A3", "数据/代码仓库链接", "占位符", "你提供 DOI/链接"],
    ["A4", "原创性与未一稿多投", "Cover_Letter_v2 已完成", "完成"],
    ["A5", "Author contributions", "占位符", "你确认"],
    ["B1", "双栏 ≤10 页", "docx 单栏 12–13 页；双栏未实测", "排版后测"],
    ["B2", "LaTeX + Springer 模板", "无 TeX 环境，main_v2.tex 未生成", "需装 TeX 或你排版"],
    ["B7", "参考文献卷期页/DOI", "已补卷期/页码/DOI；个别条目无卷期", "部分完成"],
    ["C1", "公式编号/残留", "已加 (1)-(5) 编号定义；其余可后补", "部分完成"],
], [1.4, 5.0, 7.0, 3.0])

doc.add_heading("3  下一步顺序", level=1)
for x in [
    "你补 A1/A3/A5：作者、单位、邮箱、ORCID、数据/代码链接、贡献分工。",
    "我补 A4 Cover Letter 与 B7 参考文献（25–41 条，卷期页 + DOI 链接）。",
    "B2 LaTeX：若本机装 TeX，我按 Springer iicol 模板重排并实测页数；否则先以 docx 双栏版估算。",
    "C1 公式编号、C2 符号表、C5 图片许可、C6 AI 声明。",
    "最后重跑 verify_numbers、冻结、哈希，生成投稿 PDF。",
]:
    doc.add_paragraph(x, style="List Bullet")

doc.add_heading("4  结论", level=1)
p("内容收窄已完成：正文从 5,600+ 词降到约 4,800 词，RQ3/自然/端到端全部进 SI，主表改为全 13 段，4 表 2 图，Statements 模板已加。"
  "但 A1/A3/A4/A5、B2/B7 仍未完成，因此现在仍不是“可提交”状态。")
p("外部依赖只有三类：作者信息、数据/代码链接、LaTeX 环境。前两项你提供后，我可以在 1–2 天内完成 A4/B7/C1/C2；"
  "LaTeX 需要本机有 TeX 或你那边排版。")

doc.save(OUT)
print("saved", OUT)
