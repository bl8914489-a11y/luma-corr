"""Build a short DOCX guide for viewing the visualizations."""
from __future__ import annotations

import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT = os.path.join(WS, "可视化", "可视化查看说明.docx")
SAMPLE = os.path.join(WS, "可视化", "frames", "sailboat_B_len12", "034.png")

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.0)
    s.top_margin = s.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]
st.font.name = "宋体"; st.font.size = Pt(10.5)


def p(text, bold=False, size=10.5):
    par = doc.add_paragraph()
    r = par.add_run(text)
    r.font.bold = bold; r.font.size = Pt(size)
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")
    return par


doc.add_heading("局部亮度校正 · 可视化查看说明", level=0)
p("本目录有 4 个案例，每个案例包含：逐帧五联 PNG、8 fps 演示 GIF、网页播放器数据。"
  "所有像素来自真实运行（参考帧 / 注入后 / A3 / A4 / A7），不是示意图。", size=11)

doc.add_heading("一、推荐：网页播放器", level=1)
for step in [
    "双击 可视化/打开可视化.cmd（或直接双击 index.html）。若 .cmd 被安全软件拦截，直接双击 index.html 即可。",
    "浏览器请用 Edge 或 Chrome；不要用微信内置浏览器。",
    "左上四个按钮切换案例；▶ 播放 / ⏸ 暂停；◀ / ▶ 逐帧；下拉调 4/8/12/16 fps；拖进度条跳帧。",
    "当前帧在缺陷区间 [30,42) 时，画面外框变红，右上角显示 IN DEFECT。",
    "右侧表格显示当前帧与区间内均值 Y MAE。",
]:
    doc.add_paragraph(step, style="List Number")

doc.add_heading("二、MP4（最通用）", level=1)
p("双击任一 .mp4，用系统播放器或 Edge/Chrome 打开（8 fps 演示，76 帧约 9.5 秒，约 2 MB）。")
p("sailboat_A_len12.mp4 / sailboat_B_len12.mp4 / horse_A_len12.mp4 / book_B_len12.mp4")
doc.add_heading("三、直接看 GIF", level=1)
p("双击任一 .gif 即可（8 fps，76 帧约 9.5 秒，约 5 MB）。"
  "Windows「照片」可能只显示第一帧；若如此，右键 → 打开方式 → Edge/Chrome，或把 GIF 拖进浏览器。")
p("sailboat_A_len12.gif / sailboat_B_len12.gif / horse_A_len12.gif / book_B_len12.gif")

doc.add_heading("四、逐帧 PNG", level=1)
p("frames/<case>/000.png … 075.png 是 1424×336 的五联图，可直接放进 PPT 或论文附录；"
  "metrics.json 是逐帧 Y MAE 与亮度记录。")

doc.add_heading("五、四个案例看什么", level=1)
cases = json.load(open(os.path.join(WS, "可视化", "cases.json"), encoding="utf-8"))
table = doc.add_table(rows=1, cols=4)
table.style = "Table Grid"
for i, h in enumerate(["案例", "看点", "A3 区间均值", "A7 区间均值"]):
    cell = table.rows[0].cells[i]; cell.text = ""
    r = cell.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(9)
for c in cases:
    cells = table.add_row().cells
    vals = [c["id"], c["note"].split("  GIF")[0], f"{c['interval_mean_y_mae']['A3']:.2f}",
            f"{c['interval_mean_y_mae']['A7']:.2f}"]
    for i, v in enumerate(vals):
        cells[i].text = ""
        r = cells[i].paragraphs[0].add_run(v); r.font.size = Pt(8.5)
for row in table.rows:
    for i, w in enumerate([5.0, 8.0, 2.6, 2.6]):
        row.cells[i].width = Cm(w)

doc.add_heading("六、样例帧", level=1)
p("下面是 sailboat_B_len12 的第 34 帧（区间内）。左起：参考 | 注入后 | A3 | A4 | A7。")
if os.path.exists(SAMPLE):
    doc.add_picture(SAMPLE, width=Cm(16.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
p("读法：A3 在该帧 Y MAE 5.53，A7 为 0.84；A4 因为全序列中值在 12 帧区间内被污染，"
  "区间内等于未修正（56.15），这就是结果表里 A2=A4 的区间内数值、以及 A4 边界误差的来源。", size=9.5)

doc.add_heading("七、必须注意", level=1)
for x in [
    "8 fps 只是演示帧率，不是数据集真实 FPS；归档没有提供 FPS，本目录没有把它写成真实时间。",
    "MP4 由项目内置 imageio-ffmpeg 编码（8 fps 演示），未改变帧内容，不是数据集真实 FPS。",
    "GIF 是逐帧 PNG 缩小 50% 后播放；原始分辨率看 frames/。",
    "五联图的 Y MAE 是 Y 通道整帧平均绝对误差，与结果表口径一致。",
]:
    doc.add_paragraph(x, style="List Bullet")

p("重新生成：python project/tools/build_visualizations.py；python project/tools/build_html_viewer.py",
  size=9.5)

doc.save(OUT)
print("saved", OUT)
