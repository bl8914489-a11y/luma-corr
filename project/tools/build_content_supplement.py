"""Build the content-strengthening supplement (no paper/typesetting)."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "报告", "内容补强_全13段与端到端_2026-11-21.docx")

FULL = {
    "A": {
        "A1": (19.90, 19.89, 19.90), "A2": (2.29, 18.26, 19.52), "A3": (2.06, 1.48, 2.40),
        "A4": (2.29, 18.26, 19.52), "A5": (2.02, 1.87, 3.09), "A6": (20.35, 20.25, 20.31),
        "A7": (3.37, 3.25, 3.81), "A7f": (32.87, 33.02, 33.11), "A8": (7.94, 18.88, 20.36),
        "A9": (2.14, 1.98, 3.42)},
    "B": {
        "A1": (53.62, 53.68, 54.02), "A2": (8.55, 52.05, 53.66), "A3": (8.16, 7.65, 8.07),
        "A4": (8.55, 52.05, 53.66), "A5": (2.53, 2.40, 3.52), "A6": (33.64, 33.33, 33.51),
        "A7": (2.59, 1.97, 2.95), "A7f": (1.46, 1.48, 1.45), "A8": (8.37, 50.42, 53.48),
        "A9": (8.35, 8.17, 8.75)},
    "B13": {
        "A1": (20.49, 20.54, 20.63), "A2": (4.18, 18.83, 20.26), "A3": (3.92, 3.20, 4.03),
        "A4": (4.18, 18.83, 20.26), "A5": (2.12, 1.97, 3.16), "A6": (21.30, 21.16, 21.27),
        "A7": (2.11, 1.48, 2.50), "A7f": (32.24, 32.39, 32.42), "A8": (7.84, 19.54, 21.16),
        "A9": (3.93, 3.79, 4.77)},
}
COST = [("A1", "noop", 0.0172, 1.43), ("A2", "local median", 0.2666, 22.22),
        ("A3", "outside linear", 0.2663, 22.20), ("A4", "global median", 0.8533, 71.11),
        ("A5", "histogram STE", 0.3977, 33.14), ("A6", "CLAHE", 0.4419, 36.83),
        ("A7", "adaptive gamma", 2.1374, 178.12), ("A7f", "fixed inverse gamma", 0.3180, 26.50),
        ("A8", "temporal bilateral", 1.5790, 131.58), ("A9", "Kalman/RTS", 0.2692, 22.44)]


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


def main():
    global _DOC
    doc = Document(); _DOC = doc
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(1.9)
    st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

    doc.add_heading("内容补强报告：全 13 段主表与检测→校正端到端", level=0)
    p("2026-11-21 · 只补内容，不写论文、不排版", size=11)
    p("针对 SIVP 投稿评估报告中的 P1-1（主表口径）、RQ3 误差传导、计算成本与复现缺口，本报告做四件事："
      "（1）给出全 13 段完整矩阵；（2）报告 A7f/A5 的新发现并修正“A7 普适最优”的表述；"
      "（3）给出 CUSUM 预测区间→局部校正的端到端误差；（4）补 CPU 成本表与 B2 耗时证据。")

    h = doc.add_heading
    h("1  全 13 段主表（Y-MAE，越低越好）", level=1)
    p("此前 Table 1 用的是 3 段开发集，全 13 段数字差一倍以上。下表全部为 13 段均值，按注入和长度分组；"
      "95% bootstrap CI 在 `results/tables/full13_matrix.csv`，正文只列均值。")
    for inj, label in (("A", "A：RGB −20"), ("B", "B：gamma 2.0"), ("B′", "B′：gamma 1.3")):
        key = "B13" if inj == "B′" else inj
        p(label, bold=True)
        table(doc, ["方法", "len1", "len4", "len12"], [
            [m, f"{FULL[key][m][0]:.2f}", f"{FULL[key][m][1]:.2f}", f"{FULL[key][m][2]:.2f}"]
            for m in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A7f", "A8", "A9")
        ], [3.0, 3.0, 3.0, 3.0])

    h("1.1  全 13 段改变了什么", level=2)
    for x in [
        "A 注入：A3 仍是最好（2.06/1.48/2.40），但 A5 在 len1 略低（2.02），A3 的优势没有开发集那么大。",
        "B 注入：A7f 固定逆 gamma 最好（1.46/1.48/1.45），A5 2.53/2.40/3.52，A7 2.59/1.97/2.95；A7 不是 B 的最优。",
        "B′ 注入：A7 最好（2.11/1.48/2.50），A5 2.12/1.97/3.16，A3 3.92/3.20/4.03；A5 在 len1 与 A7 基本持平。",
        "胜率：B 注入 A7f/A7/A5 都对 A3 13/13 胜；B′ 注入 A5 对 A3 13/13/11/13 胜，A7 12/13；A 注入 A7 只有 2/13 胜。",
        "结论应改为“分注入选型”：A→A3，B→A7f（已知 gamma=2）或 A7/A5，B′→A7/A5；不能再写“A7 是 gamma 的通用最优”。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h("2  检测→校正端到端（CUSUM 预测区间）", level=1)
    p("设置：13 段 × A/B/B′ × len4/12，start=30；CUSUM(k=0.5,h=8,min_len=2) 输出预测 span；"
      "对预测 span 施加局部校正；评价仍在真实区间上。Oracle 表示直接对真实区间校正，是上界。")
    table(doc, ["方法", "Oracle Y-MAE", "Detected Y-MAE", "检测代价 Δ", "Detected OutFrac"], [
        ["A3", "4.47", "7.57", "+3.10", "4.0%"],
        ["A5", "2.67", "5.66", "+2.99", "4.6%"],
        ["A7", "2.66", "5.85", "+3.19", "3.9%"],
        ["A7f", "22.31", "21.60", "−0.71", "5.5%"],
    ], [2.4, 3.2, 3.2, 2.8, 3.2])
    p("A7f 的 oracle 均值被 A/B′ 拖坏（它对 A/B′ 不适用），不能看总均值；按注入拆开如下。")
    table(doc, ["注入", "A3 oracle→detected", "A5 oracle→detected", "A7 oracle→detected", "A7f oracle→detected"], [
        ["A", "1.94→4.86", "2.48→5.28", "3.53→6.34", "33.07→30.49"],
        ["B", "7.86→10.60", "2.96→5.60", "2.46→5.36", "1.46→4.37"],
        ["B′", "3.62→7.25", "2.56→6.09", "1.99→5.85", "32.40→29.95"],
    ], [2.0, 3.4, 3.4, 3.4, 3.6])
    for x in [
        "检测误差把校正误差放大约 1.4–3.0 倍：A3 在 A 注入 1.94→4.86，B 注入 7.86→10.60，B′ 3.62→7.25。",
        "预测 span 在真实区间外也会改像素：Detected OutFrac 约 3.9%–5.5%，这是“检测漏/多报”直接造成的区间外改动。",
        "检测不确定时，A5 的 detected 总均值 5.66 最好，A7 5.85 次之，A3 7.57 最差；这与 oracle 下 A3 最好相反，说明选型要看检测质量。",
        "B 注入若已知 gamma=2，A7f detected 4.37 最好；但 A7f 不能用于 A/B′，不能作为通用方法。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h("3  CPU 成本（单段 76 帧 512×512，A 注入 len12，两次取最小）", level=1)
    table(doc, ["方法", "类型", "总秒", "ms/帧"], [
        [m, k, f"{s:.3f}", f"{ms:.1f}"] for m, k, s, ms in COST
    ], [2.0, 5.0, 3.0, 3.0])
    p("A3 约 22 ms/帧，A7 约 178 ms/帧，A8 约 132 ms/帧；B2 每案例约 8.9 分钟 GPU，"
      "相差 4–5 个数量级。对应用型期刊，这个成本对比是相对深度方法的实际优势。")

    h("4  实用选型建议（可作为论文的实践结论）", level=1)
    table(doc, ["条件", "推荐", "依据"], [
        ["已知是加性偏移，或检测区间较准", "A3", "A 注入 2.06/1.48/2.40，oracle 最好"],
        ["已知 gamma=2.0（B）", "A7f", "1.46/1.48/1.45，B 注入最优"],
        ["gamma 未知，或 A/B/B′ 混合", "A5 或 A7", "A5 detected 5.66 最好；A7 5.85，A3 7.57"],
        ["gamma 1.3（B′）", "A7", "2.11/1.48/2.50，B′ 最优；A5 接近"],
        ["检测可能漏/多报", "A5 优先，A3 降级", "检测误差下 A3 从 4.47 涨到 7.57"],
        ["贴边（start=0 或 end=N）", "A3e", "start0 len1 9.41→3.06；但仍未追平原中部"],
        ["多区间", "逐段独立校正", "2/3/4 段 OutFrac 0%；检测仍是瓶颈"],
    ], [5.5, 4.0, 7.0])

    h("5  B2 耗时与日志证据", level=1)
    table(doc, ["批次", "案例", "总耗时", "每案例", "stage2"], [
        ["单区间 Full（新增）", "78", "11.56 h", "8.89 min", "~12 s"],
        ["单区间 len12（新增）", "24", "3.51 h", "8.78 min", "~12 s"],
        ["两区间", "52", "7.67 h", "8.85 min", "~12 s"],
        ["三段", "26", "约 3.9 h", "约 8.9 min", "~11 s"],
        ["四段", "13", "1.94 h", "8.95 min", "~12 s"],
    ], [5.0, 2.0, 3.2, 3.0, 3.0])
    p("样例 stage1/stage2 日志已放入 `results/b2_logs/`（3 个案例，共 6 个日志）。配置：512×512、down=4、"
      "iters_num=10001、RTX 5060 8GB。此前“8.7 分钟/案例”现在有实测与日志支撑。")

    h("6  复现包修正（已做/待做）", level=1)
    for x in [
        "已做：`verify_numbers.py` 支持 `FREEZE_OUT` 环境变量；一键测试把冻结写到临时文件，跑完不再改写包内 FREEZE。",
        "已做：补 3 个 B2 案例的 stage1/stage2 日志与 B2 耗时表。",
        "已做：全 13 段矩阵 CSV 与 bootstrap CI 写入 results/tables/full13_matrix.csv。",
        "待做：一键测试的 Python fallback 仍含本机路径；换机需设 LUMA_PY/LUMA_WS（README 已写）。",
        "待做：SHA256SUMS 需在最终一次打包后重算；若先跑测试再打包，哈希会不一致。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    h("7  对论文主张的影响（暂不改稿件）", level=1)
    for x in [
        "主表必须改全 13 段，开发集放补充；否则“只报 3 段”会被直接质疑。",
        "“A7 是 gamma 通用最优”要改成“A7f 在 B 最优、A7 在 B′ 最优、A5 在检测不确定时最稳”。",
        "“局部写回不改区间外”要补一句：检测预测 span 会带来 3.9%–5.5% 的真实区间外改动，这是检测误差的代价。",
        "“检测误差传导”现在有数字：校正误差约放大 1.4–3.0 倍，不再只是定性说法。",
        "实践选型表可以直接作为论文的“工程建议”，弥补“没有新方法”的说服力缺口。",
    ]:
        doc.add_paragraph(x, style="List Bullet")

    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
