"""Create the annotation template, guide and zip package."""
from __future__ import annotations

import csv
import os
import shutil
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "标注")
ZIP = os.path.join(OUT, "标注包_2026-11-18.zip")
index = list(csv.DictReader(open(os.path.join(OUT, "clip_index.csv"), encoding="utf-8")))


def template():
    wb = Workbook()
    ws = wb.active; ws.title = "填写说明"
    lines = [
        ("视频标注说明", True),
        ("", False),
        ("1. 每个 clip 是一个 24 帧的短视频，顶部已烧录 clip 编号、帧号（0-23）和全局帧号。", False),
        ("2. 先正常播放一遍，再逐帧检查；只判断“整体亮度/曝光是否出现异常”。", False),
        ("3. 若存在异常，has_defect 填 1，并填 defect_start / defect_end（0-23，含首尾）。", False),
        ("4. 若没有异常，has_defect 填 0，type 填 none，start/end 留空。", False),
        ("5. 不要根据文件名猜注入；不要和另一位标注者讨论。", False),
        ("6. 不确定时 confidence 填 1，并在 notes 写原因。", False),
        ("7. 两个标注者分别填 Annotator_A / Annotator_B；20% 片段会被双标用于一致性。", False),
        ("", False),
        ("类型：flicker（快速抖动）、exposure（持续偏移/台阶）、gamma（中间调/对比度变化）、other。", False),
        ("严重度 1-5：1 几乎看不出；3 明显但不影响观看；5 一眼可见、主导画面。", False),
        ("置信度 1-3：1 不确定；2 较确定；3 非常确定。", False),
    ]
    for i, (t, b) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t); c.font = Font(bold=b, size=13 if i == 1 else 10)
    ws.column_dimensions["A"].width = 110

    headers = ["clip_id", "sequence", "clip_start", "clip_end", "has_defect", "defect_start", "defect_end",
               "type", "severity_1_5", "confidence_1_3", "notes"]
    for name in ("Annotator_A", "Annotator_B"):
        sh = wb.create_sheet(name)
        sh.append(headers)
        for c in sh[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F5597")
            c.alignment = Alignment(horizontal="center", wrap_text=True)
        for r in index:
            sh.append([r["clip_id"], r["sequence"], int(r["clip_start"]), int(r["clip_end"]), "", "", "", "", "", "", ""])
        widths = [10, 12, 10, 10, 10, 12, 12, 10, 12, 12, 40]
        for i, w in enumerate(widths, 1):
            sh.column_dimensions[chr(64 + i)].width = w
        sh.freeze_panes = "A2"
        dv1 = DataValidation(type="list", formula1='"0,1"', allow_blank=True); sh.add_data_validation(dv1)
        dv2 = DataValidation(type="list", formula1='"none,flicker,exposure,gamma,other"', allow_blank=True); sh.add_data_validation(dv2)
        dv3 = DataValidation(type="list", formula1='"1,2,3,4,5"', allow_blank=True); sh.add_data_validation(dv3)
        dv4 = DataValidation(type="list", formula1='"1,2,3"', allow_blank=True); sh.add_data_validation(dv4)
        dv1.add(f"E2:E{len(index)+1}"); dv2.add(f"H2:H{len(index)+1}")
        dv3.add(f"I2:I{len(index)+1}"); dv4.add(f"J2:J{len(index)+1}")
    wb.save(os.path.join(OUT, "标注模板_2026-11-18.xlsx"))


def guide():
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2); s.top_margin = s.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

    def p(text, bold=False, size=10.5):
        par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(4)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
        r.font.name = "Times New Roman"
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")

    doc.add_heading("视频亮度缺陷标注指南", level=0)
    p("版本 2026-11-18 · 100 个 24 帧片段 · 双人独立标注", size=11)

    doc.add_heading("一、你要判断什么", level=1)
    p("只看“整体亮度/曝光是否异常”，不评价画质、内容、美观。一个亮度缺陷是：连续至少 2 帧的整体亮度、曝光或对比度变化，"
      "且不能用场景内容、物体运动、镜头运动、剪辑或原本就有的光照变化解释。")
    p("四类：flicker（快速抖动）、exposure（持续偏移/台阶）、gamma（中间调/对比度变化）、other（无法归类）。")

    doc.add_heading("二、每个片段怎么标", level=1)
    for x in [
        "1. 先按正常速度看一遍（8 fps，约 3 秒），记下可疑位置。",
        "2. 再逐帧看：VLC 用 E（下一帧）/ D（上一帧）；mpv 用 . / ,。顶部烧录的 frame 00–23 就是局部帧号。",
        "3. 没有缺陷：has_defect=0，type=none，start/end 留空。",
        "4. 有缺陷：has_defect=1，填 defect_start / defect_end（0–23，含首尾）；多段只标最主要的一段，其他写 notes。",
        "5. type 选一类；severity 1–5；confidence 1–3。",
        "6. 缺陷从片段外开始/结束：start 填 0 或 end 填 23，并在 notes 写“截断”。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    doc.add_heading("三、严重度与置信度", level=1)
    t = doc.add_table(rows=1, cols=2); t.style = "Table Grid"
    hdr = ["分值", "含义"]
    for i, h in enumerate(hdr):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(9)
    for a, b in [("1", "几乎看不出，只有逐帧对比才发现"), ("2", "轻微，正常播放不太注意"),
                 ("3", "明显，但不影响观看"), ("4", "很显眼，影响观看"), ("5", "一眼可见，主导画面")]:
        cells = t.add_row().cells; cells[0].text = a; cells[1].text = b
    p("置信度：1=不确定，2=较确定，3=非常确定。不确定就填 1 并写 notes，不要猜。")

    doc.add_heading("四、五个示例（先看，再开始）", level=1)
    for x in [
        "示例1_干净_sailboat.mp4：无缺陷，has_defect=0。",
        "示例2_偏移20_sailboat.mp4：第 4–15 帧整体变暗，exposure，severity 4。",
        "示例3_gamma2_book.mp4：中间调整体变暗、对比变化，gamma，severity 4。",
        "示例4_gamma1.3_horse.mp4：轻微 gamma 变化，severity 2，confidence 2。",
        "示例5_干净_horse.mp4：无缺陷。",
    ]:
        doc.add_paragraph(x, style="List Bullet")
    p("示例只用于校准“什么算缺陷”，不计入 100 个正式片段。")

    doc.add_heading("五、独立性、时间与质量", level=1)
    for x in [
        "两位标注者独立完成，不讨论、不互相看表；每人约 2.5–3.5 小时，建议分 3 次。",
        "20% 片段会被双标：用于 Cohen's kappa（是否有缺陷）与区间 IoU；目标 kappa≥0.6、IoU≥0.5。",
        "低于目标时，由第三人仲裁争议片段；仲裁只改争议项。",
        "不要根据 clip 编号、文件名或序列名推测“应该有没有缺陷”；只看画面。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    doc.add_heading("六、常见问题", level=1)
    qa = [
        ("物体本身在动导致局部亮度变化，算吗？", "不算；只算整体亮度/曝光。"),
        ("镜头运动/场景切换导致整体变亮？", "不算；需要是“无法由内容解释”的异常。"),
        ("只有 1 帧跳变？", "不算持续缺陷；可写 notes。"),
        ("有多个缺陷段？", "标最主要的一段，其余写 notes。"),
        ("拿不准？", "confidence=1，notes 写原因；不要硬判。"),
    ]
    for q, a in qa:
        p("Q：" + q, bold=True); p("A：" + a)

    doc.add_heading("七、交付", level=1)
    p("把填好的 Excel 另存为 标注模板_你的名字.xlsx，连同 notes 发回。不要改 clip_id / sequence / clip_start / clip_end 四列。")
    doc.save(os.path.join(OUT, "标注指南_2026-11-18.docx"))


def quick():
    txt = """# 标注速查卡

- 100 个 24 帧片段，顶部有 clip 编号和 frame 00–23。
- 只判断整体亮度/曝光异常，不管内容/美观。
- 先正常播放，再逐帧（VLC: E/D；mpv: ./,）。
- 无缺陷：has_defect=0，type=none。
- 有缺陷：has_defect=1，start/end 填 0–23（含首尾），type/severity/confidence。
- 多段只标主段，其余写 notes；截断写 notes。
- 不确定：confidence=1 + notes，不要猜。
- 两人独立，20% 双标；约 2.5–3.5 小时。
"""
    open(os.path.join(OUT, "标注速查卡.md"), "w", encoding="utf-8").write(txt)


def zipit():
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                if f == os.path.basename(ZIP):
                    continue
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, OUT))
    print("zip", round(os.path.getsize(ZIP) / 1e6, 1), "MB")


if __name__ == "__main__":
    template(); guide(); quick(); zipit()
    print("done")
